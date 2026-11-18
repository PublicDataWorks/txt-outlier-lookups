import types
from unittest.mock import MagicMock, call, patch

import pytest
import sentry_sdk
from llama_index.core.base.llms.types import CompletionResponse
from loguru import logger
from sqlalchemy.exc import OperationalError

import configs.llm  # noqa: F401
from configs import database

# text_summary reads max_tokens from the database at import; see tests/test_search_service.py.
with patch.object(database, "Session") as stub_session:
    stub_session.return_value.query.return_value.filter.return_value.first.return_value = types.SimpleNamespace(
        content="1000"
    )
    import configs.query_engine.text_summary  # noqa: F401

from libs.missive_sender import FALLBACK  # noqa: E402
from services import lookup_retries  # noqa: E402
from services.lookup_retries import LookupRetries  # noqa: E402
from services.services import search_service  # noqa: E402
from templates.templates import templates  # noqa: E402

PHONE = "+15550001234"
RESIDENT_TEXT = "1111 E. Jefferson, my landlord won't fix the heat"
ANSWER = "The county has JANE OWNER listed as the owner."
LOOKUP_ERROR_SMS = "Sorry, test lookup error text."
# One property row: owner, address, rental_status, tax_status, zip_code, tax_due.
ROW = ("JANE OWNER", "1111 E JEFFERSON AVE", "IS NOT", "OK", "48207", "0")


@pytest.fixture
def logs():
    records = []
    sink = logger.add(lambda message: records.append(message.record), level="DEBUG")
    yield records
    logger.remove(sink)


@pytest.fixture
def sentry_events():
    events = []

    def record_instead_of_sending(event, hint):
        events.append(event)
        return None

    sentry_sdk.init(dsn="http://public@127.0.0.1:1/1", before_send=record_instead_of_sending)
    yield events
    sentry_sdk.init()


@pytest.fixture
def waits():
    with patch("services.lookup_retries.sleep") as sleep:
        yield sleep


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def calls(*outcomes):
    """A stand-in for a lookup step: raises each exception and returns each other value, in order."""
    step = MagicMock(side_effect=list(outcomes))
    return step


def is_blank(answer):
    return not str(answer).strip()


# The retry helper on its own.

def test_a_step_that_works_first_time_is_not_retried_or_reported(waits, logs, sentry_events):
    step = calls("result")

    assert LookupRetries("conversation-1").run("address parser", step) == "result"

    assert step.call_count == 1
    waits.assert_not_called()
    assert [record for record in logs if "lookup_retry" in record["message"]] == []
    assert sentry_events == []


def test_a_step_that_fails_once_is_retried_and_returns_its_result(waits):
    step = calls(TimeoutError("OpenAI timed out"), "result")

    assert LookupRetries("conversation-1").run("address parser", step) == "result"

    assert step.call_count == 2
    assert waits.call_args_list == [call(1)]


def test_a_step_that_keeps_failing_is_tried_three_times_then_raises_the_last_error(waits):
    step = calls(TimeoutError("first"), OperationalError("select", {}, Exception("dropped")), KeyError("address"))

    with pytest.raises(KeyError):
        LookupRetries("conversation-1").run("address parser", step)

    assert step.call_count == lookup_retries.ATTEMPTS == 3
    # The whole added wait is four seconds, plus the tries themselves.
    assert waits.call_args_list == [call(1), call(3)]


def test_an_empty_answer_is_retried_once(waits):
    step = calls(CompletionResponse(text=" "), CompletionResponse(text=ANSWER))

    assert str(LookupRetries("conversation-1").run("owner summary", step, is_empty=is_blank)) == ANSWER

    assert step.call_count == 2
    assert waits.call_args_list == [call(1)]


def test_an_answer_that_stays_empty_is_returned_after_one_retry(waits):
    step = calls(CompletionResponse(text=" "), CompletionResponse(text=""), "never reached")

    assert str(LookupRetries("conversation-1").run("owner summary", step, is_empty=is_blank)) == ""

    assert step.call_count == lookup_retries.EMPTY_ATTEMPTS == 2


def test_no_retry_starts_once_the_lookup_has_run_out_of_time(waits):
    clock = Clock()
    retries = LookupRetries("conversation-1", clock=clock)
    clock.now += lookup_retries.RETRY_BUDGET_SECONDS
    step = calls(TimeoutError("OpenAI timed out"), "never reached")

    with pytest.raises(TimeoutError):
        retries.run("owner summary", step)

    assert step.call_count == 1
    waits.assert_not_called()


def test_the_time_budget_is_shared_by_every_step_of_a_lookup(waits):
    clock = Clock()
    retries = LookupRetries("conversation-1", clock=clock)

    def slow_parser():
        clock.now += lookup_retries.RETRY_BUDGET_SECONDS
        return "1111 E JEFFERSON AVE", None

    retries.run("address parser", slow_parser)
    step = calls(TimeoutError("database timed out"), "never reached")

    with pytest.raises(TimeoutError):
        retries.run("property query", step)
    assert step.call_count == 1


def test_a_rescue_is_logged_and_counted_in_one_sentry_issue_per_step(waits, logs, sentry_events):
    LookupRetries("conversation-1").run("address parser", calls(TimeoutError("x"), "result"))
    LookupRetries("conversation-2").run("address parser", calls(TimeoutError("x"), TimeoutError("y"), "result"))

    assert [record["message"] for record in logs if "recovered" in record["message"]] == [
        "[lookup_retry] address parser recovered on try 2 for conversation conversation-1 (failures: TimeoutError)",
        "[lookup_retry] address parser recovered on try 3 for conversation conversation-2 "
        "(failures: TimeoutError, TimeoutError)",
    ]
    assert [(event["level"], event["fingerprint"], event["message"], event["tags"]) for event in sentry_events] == [
        ("info", ["lookup-retry", "address parser", "recovered"], "Lookup address parser recovered on a retry",
         {"step": "address parser", "outcome": "recovered", "tries": "2", "first_failure": "TimeoutError",
          "conversation_id": "conversation-1"}),
        ("info", ["lookup-retry", "address parser", "recovered"], "Lookup address parser recovered on a retry",
         {"step": "address parser", "outcome": "recovered", "tries": "3", "first_failure": "TimeoutError",
          "conversation_id": "conversation-2"}),
    ]


def test_a_step_that_never_recovers_is_logged_and_counted_as_gave_up(waits, logs, sentry_events):
    with pytest.raises(TimeoutError):
        LookupRetries("conversation-1").run("owner summary", calls(*[TimeoutError("x")] * 3))

    assert [record["message"] for record in logs if "gave up" in record["message"]] == [
        "[lookup_retry] owner summary gave up after 3 tries for conversation conversation-1 "
        "(failures: TimeoutError, TimeoutError, TimeoutError)",
    ]
    [event] = sentry_events
    assert (event["level"], event["fingerprint"], event["tags"]["outcome"], event["tags"]["tries"]) == (
        "warning", ["lookup-retry", "owner summary", "gave_up"], "gave_up", "3"
    )


def test_a_failing_sentry_report_does_not_break_the_lookup(waits, logs):
    with patch("services.lookup_retries.sentry_sdk.capture_message", side_effect=RuntimeError("sentry down")):
        assert LookupRetries("conversation-1").run("address parser", calls(TimeoutError("x"), "result")) == "result"

    assert "Reporting a lookup retry to Sentry failed: RuntimeError" in [record["message"] for record in logs]


def test_retry_logs_and_reports_name_the_error_type_only(waits, logs, sentry_events):
    secret = TimeoutError(f"{RESIDENT_TEXT} {PHONE}")
    LookupRetries("conversation-1").run("address parser", calls(secret, "result"))

    reported = " ".join(record["message"] for record in logs) + repr(sentry_events)
    assert "Jefferson" not in reported and PHONE[2:] not in reported


# A whole lookup: a step that fails once and then works sends the normal reply.

@pytest.fixture
def missive(monkeypatch, waits):
    monkeypatch.setenv("MISSIVE_LOOKUP_FAILED_TAG_ID", "lookup-failed-tag")
    monkeypatch.setenv("MISSIVE_LOOKUP_TAG_ID", "lookup-tag")
    with patch("services.lookup_failures.missive_client") as reports, \
            patch("services.lookup_failures.get_template_content_by_name",
                  side_effect={"lookup_error": LOOKUP_ERROR_SMS}.get), \
            patch("services.services.missive_client") as replies, \
            patch("services.services.time.sleep"):
        yield types.SimpleNamespace(reports=reports, replies=replies)


def lookup(parser=None, query=None, summary=None, history=None):
    parser = parser or calls(("1111 E JEFFERSON AVE", None))
    query = query or calls([ROW])
    summary = summary or calls(ANSWER)
    with patch("services.services.extract_address_information_with_llm", parser), \
            patch("services.services.classify_unparseable_text", return_value="other"), \
            patch("services.services.Session", MagicMock()), \
            patch("services.services.query_mi_wayne_detroit", query), \
            patch("services.services.add_data_lookup_to_db", history or MagicMock()), \
            patch("services.services.owner_query_engine_without_sunit", summary), \
            patch("services.services.get_template_content_by_name", side_effect=templates.get):
        return search_service(query=RESIDENT_TEXT, conversation_id="conversation-1", to_phone=PHONE)


def answer_sent(missive):
    return missive.replies.send_sms_sync.call_args_list[0].args[0] == ANSWER


def assert_nothing_reported(missive):
    missive.reports.queue_post.assert_not_called()
    missive.reports.send_sms_sync.assert_not_called()


def test_an_address_parser_that_fails_once_still_gets_the_resident_their_answer(missive):
    parser = calls(TimeoutError("OpenAI timed out"), ("1111 E JEFFERSON AVE", None))

    assert lookup(parser=parser) == ({"result": ANSWER}, 200)

    assert parser.call_count == 2
    assert answer_sent(missive)
    assert_nothing_reported(missive)


def test_a_property_query_that_fails_once_still_gets_the_resident_their_answer(missive):
    query = calls(OperationalError("select", {}, Exception("connection dropped")), [ROW])

    assert lookup(query=query) == ({"result": ANSWER}, 200)

    assert query.call_count == 2
    assert answer_sent(missive)
    assert_nothing_reported(missive)


def test_each_property_query_try_gets_its_own_database_session(missive):
    sessions = MagicMock()
    query = calls(OperationalError("select", {}, Exception("connection dropped")), [ROW])
    with patch("services.services.Session", sessions):
        from services.services import query_property
        retries = LookupRetries("conversation-1")
        with patch("services.services.query_mi_wayne_detroit", query):
            retries.run("property query", lambda: query_property("1111 E JEFFERSON AVE", None))

    assert sessions.call_count == 2


def test_an_owner_summary_that_fails_once_still_gets_the_resident_their_answer(missive):
    summary = calls(TimeoutError("OpenAI timed out"), ANSWER)

    assert lookup(summary=summary) == ({"result": ANSWER}, 200)

    assert answer_sent(missive)
    assert_nothing_reported(missive)


def test_an_owner_summary_that_comes_back_empty_once_still_gets_the_resident_their_answer(missive):
    summary = calls(CompletionResponse(text=" "), CompletionResponse(text=ANSWER))

    assert lookup(summary=summary) == ({"result": ANSWER}, 200)

    assert summary.call_count == 2
    assert answer_sent(missive)
    assert_nothing_reported(missive)


def test_an_owner_summary_that_stays_empty_gets_the_error_text_after_one_retry(missive):
    summary = calls(CompletionResponse(text=" "), CompletionResponse(text=" "))

    assert lookup(summary=summary) == ("", 200)

    assert summary.call_count == 2
    missive.replies.send_sms_sync.assert_not_called()
    assert missive.reports.send_sms_sync.call_args_list == [
        call(LOOKUP_ERROR_SMS, PHONE, "conversation-1", role=FALLBACK)
    ]


def test_a_step_that_keeps_failing_raises_to_the_catch_all_without_texting_anything(missive):
    summary = calls(*[TimeoutError("OpenAI timed out")] * 3)

    with pytest.raises(TimeoutError):
        lookup(summary=summary)

    assert summary.call_count == 3
    # /search's catch-all reports it and texts the resident, once (see test_lookup_failures).
    missive.replies.send_sms_sync.assert_not_called()
    assert_nothing_reported(missive)


def test_failing_to_save_the_lookup_history_does_not_cost_the_resident_their_answer(missive, logs):
    history = MagicMock(side_effect=OperationalError("insert", {}, Exception("connection dropped")))

    assert lookup(history=history) == ({"result": ANSWER}, 200)

    assert answer_sent(missive)
    assert_nothing_reported(missive)
    assert "Saving the lookup history failed for conversation conversation-1: OperationalError" in [
        record["message"] for record in logs
    ]


def test_a_parser_that_finds_no_address_is_not_retried(missive):
    parser = calls((None, None), "never reached")

    assert lookup(parser=parser) == ({"message": "Couldn't parse address from query"}, 200)

    assert parser.call_count == 1


def test_no_match_is_not_retried(missive):
    query = calls([], "never reached")

    lookup(query=query)

    assert query.call_count == 1


def test_the_lookup_error_text_is_the_wording_outlier_approved():
    # Kate approved this exact text on Nov 18 (OUT-416). Change it only with Outlier's sign-off.
    assert templates["lookup_error"] == (
        "Sorry, we had an error. A reporter will follow up, usually within 48 hours. "
        "You can try another address or text MENU for more options."
    )
    # One SMS segment.
    assert len(templates["lookup_error"]) <= 160
