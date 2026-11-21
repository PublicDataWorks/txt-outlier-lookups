import json
import os
import subprocess
import sys
import threading
import time
import types
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import requests
from llama_index.core.base.llms.types import CompletionResponse
from loguru import logger

import configs.llm  # noqa: F401
from configs import database

# text_summary reads max_tokens from the database at import; see tests/test_search_service.py.
with patch.object(database, "Session") as stub_session:
    stub_session.return_value.query.return_value.filter.return_value.first.return_value = types.SimpleNamespace(
        content="1000"
    )
    import configs.query_engine.text_summary  # noqa: F401

from constants.urls import CREATE_MESSAGE_URL, CREATE_POST_URL  # noqa: E402
from libs.MissiveAPI import MissiveAPI, post_draft  # noqa: E402
from helpers import extract_address_information_with_llm  # noqa: E402
from libs.missive_sender import ANSWER, FALLBACK, FOLLOW_UP, OrderedSender  # noqa: E402
from libs.webhook_claims import CLAIM_SECONDS, claim_webhook, sweep_expired_claims  # noqa: E402
from services import lookup_failures  # noqa: E402
from services.services import search_service  # noqa: E402
from templates.templates import templates  # noqa: E402

PHONE = "+15550001234"
RESIDENT_TEXT = "1111 E. Jefferson, my landlord won't fix the heat"
FAILED_TAG = "lookup-failed-tag"
LOOKUP_TAG = "lookup-tag"
# Not the code template: a test can't depend on what a lookup_template row says.
LOOKUP_ERROR_SMS = "Sorry, test lookup error text."
ON_ITS_WAY = ("A text telling the resident a reporter will follow up was queued, but delivery isn't confirmed. "
              "If Missive drops it, another note may follow.")
REPO = Path(__file__).resolve().parents[1]
# One property row: owner, address, rental_status, tax_status, zip_code, tax_due.
ROW = ("JANE OWNER", "1111 E JEFFERSON AVE", "IS NOT", "OK", "48207", "0")


@pytest.fixture
def logs():
    records = []
    sink = logger.add(lambda message: records.append(message.record), level="DEBUG")
    yield records
    logger.remove(sink)


@pytest.fixture
def missive(monkeypatch):
    """Both Missive clients a lookup uses, so nothing reaches the real API or the real SMS queue."""
    monkeypatch.setenv("MISSIVE_LOOKUP_FAILED_TAG_ID", FAILED_TAG)
    monkeypatch.setenv("MISSIVE_LOOKUP_TAG_ID", LOOKUP_TAG)
    with patch("services.lookup_failures.missive_client") as reports, \
            patch("services.lookup_failures.get_template_content_by_name",
                  side_effect={"lookup_error": LOOKUP_ERROR_SMS}.get), \
            patch("services.services.missive_client") as replies, \
            patch("services.services.time.sleep"), \
            patch("services.lookup_retries.sleep"):
        yield types.SimpleNamespace(reports=reports, replies=replies)


def lookup(rows=(ROW,), address="1111 E JEFFERSON AVE", answer="The county has JANE OWNER listed as the owner.",
           templates_found=True, reason="contact_info"):
    def template(name):
        return None if not templates_found and name in ("no_match", "closest_match") else templates.get(name)

    with patch("services.services.extract_address_information_with_llm", return_value=(address, None)), \
            patch("services.services.classify_unparseable_text", return_value=reason), \
            patch("services.services.Session", MagicMock()), \
            patch("services.services.query_mi_wayne_detroit", return_value=list(rows)), \
            patch("services.services.add_data_lookup_to_db"), \
            patch("services.services.owner_query_engine_without_sunit", return_value=answer), \
            patch("services.services.get_template_content_by_name", side_effect=template):
        return search_service(query=RESIDENT_TEXT, conversation_id="conversation-1", to_phone=PHONE)


def posts(missive):
    return [(c.args[0], c.args[1], c.kwargs) for c in missive.reports.queue_post.call_args_list]


def resident_sms(missive):
    return missive.reports.send_sms_sync.call_args_list


def assert_no_resident_data(text):
    assert "Jefferson" not in text and "JEFFERSON" not in text and PHONE[2:] not in text


# Each path that used to end in silence.

def test_a_parse_failure_leaves_a_post_and_label_but_no_resident_text(missive):
    assert lookup(address=None, reason="contact_info") == ({"message": "Couldn't parse address from query"}, 200)

    [(markdowns, conversation, options)] = posts(missive)
    assert conversation == "conversation-1"
    assert options == {"notification_title": "Address lookup failed", "add_label_list": [FAILED_TAG]}
    assert markdowns == [
        "Automatic address lookup didn't reply: couldn't read an address in the text (contact_info). "
        "The resident wasn't texted. Please follow up by hand."
    ]
    assert resident_sms(missive) == []
    missive.replies.send_sms_sync.assert_not_called()


def test_an_empty_owner_answer_leaves_a_post_and_texts_the_resident(missive):
    # What the engine really returns; it is truthy even with no text.
    lookup(answer=CompletionResponse(text=" "))

    [(markdowns, _, options)] = posts(missive)
    assert markdowns == [
        "Automatic address lookup didn't reply: the owner lookup came back empty. "
        f"{ON_ITS_WAY} Please follow up by hand."
    ]
    assert options["add_label_list"] == [FAILED_TAG]
    assert resident_sms(missive) == [call(LOOKUP_ERROR_SMS, PHONE, "conversation-1", role=FALLBACK)]
    # No blank answer and no follow-up.
    missive.replies.send_sms_sync.assert_not_called()


@pytest.mark.parametrize("rows, template_name", [([], "no_match"), ([ROW, ROW], "closest_match")],
                         ids=["no match", "closest match"])
def test_a_missing_reply_template_leaves_a_post_and_texts_the_resident(missive, rows, template_name):
    response = lookup(rows=rows, templates_found=False)

    [(markdowns, _, _)] = posts(missive)
    assert markdowns == [
        f"Automatic address lookup didn't reply: the reply template is missing ({template_name}). "
        f"{ON_ITS_WAY} Please follow up by hand."
    ]
    assert resident_sms(missive) == [call(LOOKUP_ERROR_SMS, PHONE, "conversation-1", role=FALLBACK)]
    # Missive retries a webhook that fails, which would post and text the resident again each time.
    assert response == ({"result": ""}, 200)


def test_post_bodies_and_logs_leave_out_the_resident_text_and_number(missive, logs):
    lookup(address=None)
    lookup(answer=CompletionResponse(text=""))
    lookup(rows=[], templates_found=False)

    assert len(posts(missive)) == 3
    assert_no_resident_data(json.dumps(posts(missive)))
    assert_no_resident_data(" ".join(record["message"] for record in logs))


# The paths that already replied send exactly what they sent before, and no post.

def test_a_match_sends_the_same_replies_as_before_and_no_post(missive):
    response = lookup()

    labels = [LOOKUP_TAG]
    assert missive.replies.send_sms_sync.call_args_list == [
        call("The county has JANE OWNER listed as the owner.", conversation_id="conversation-1", to_phone=PHONE,
             add_label_list=labels),
        call(templates["match_second_message"], conversation_id="conversation-1", to_phone=PHONE,
             add_label_list=labels, role=FOLLOW_UP),
    ]
    assert response == ({"result": "The county has JANE OWNER listed as the owner."}, 200)
    missive.reports.queue_post.assert_not_called()


def test_no_match_sends_the_same_reply_as_before_and_no_post(missive):
    response = lookup(rows=[])

    expected = templates["no_match"].format(address="1111 E JEFFERSON AVE")
    assert missive.replies.send_sms_sync.call_args_list == [call(expected, PHONE, "conversation-1")]
    assert response == ({"result": expected}, 200)
    missive.reports.queue_post.assert_not_called()


def test_closest_match_sends_the_same_reply_as_before_and_no_post(missive):
    response = lookup(rows=[ROW, ROW])

    expected = templates["closest_match"].format(address="1111 E JEFFERSON AVE")
    assert missive.replies.send_sms_sync.call_args_list == [call(expected, PHONE, "conversation-1")]
    assert response == ({"result": expected}, 200)
    missive.reports.queue_post.assert_not_called()


# The report itself.

def test_without_the_label_setting_the_post_is_still_made_and_the_gap_logged(missive, monkeypatch, logs):
    monkeypatch.delenv("MISSIVE_LOOKUP_FAILED_TAG_ID")

    lookup_failures.report_lookup_failure("conversation-1", PHONE, lookup_failures.SYSTEM_ERROR, True)

    [(_, _, options)] = posts(missive)
    assert options["add_label_list"] is None
    assert "MISSIVE_LOOKUP_FAILED_TAG_ID is not set, so the lookup failure post adds no label" in [
        record["message"] for record in logs if record["level"].name == "INFO"
    ]


def test_a_failing_post_is_logged_without_resident_data_and_does_not_raise(missive, logs):
    missive.reports.queue_post.side_effect = requests.ConnectionError(f"no Missive for {PHONE}")

    lookup_failures.report_lookup_failure("conversation-1", PHONE, lookup_failures.SYSTEM_ERROR, True)

    errors = [record["message"] for record in logs if record["level"].name == "ERROR"]
    assert errors == ["Posting a lookup failure to Missive failed: ConnectionError"]
    assert all(record["exception"] is None for record in logs)


def test_a_failing_resident_text_is_logged_and_the_post_still_goes_out(missive, logs):
    missive.reports.send_sms_sync.side_effect = RuntimeError(f"no Missive for {PHONE}")

    lookup_failures.report_lookup_failure("conversation-1", PHONE, lookup_failures.SYSTEM_ERROR, True)

    [(markdowns, _, _)] = posts(missive)
    assert "The resident wasn't texted." in markdowns[0]
    errors = [record["message"] for record in logs if record["level"].name == "ERROR"]
    assert errors == ["Texting the resident about a failed lookup failed: RuntimeError"]


def test_without_a_conversation_nothing_is_sent_and_the_gap_is_logged(missive, logs):
    lookup_failures.report_lookup_failure(None, PHONE, lookup_failures.SYSTEM_ERROR, True, detail="KeyError")

    missive.reports.queue_post.assert_not_called()
    missive.reports.send_sms_sync.assert_not_called()
    assert [record["message"] for record in logs if record["level"].name == "ERROR"] == [
        "Couldn't report a lookup that didn't reply, the webhook had no conversation: system error (KeyError)"
    ]


def test_without_a_phone_number_staff_still_get_the_post(missive):
    lookup_failures.report_lookup_failure("conversation-1", None, lookup_failures.SYSTEM_ERROR, True)

    [(markdowns, _, _)] = posts(missive)
    assert "The resident wasn't texted." in markdowns[0]
    missive.reports.send_sms_sync.assert_not_called()


def test_a_dropped_answer_is_reported_to_staff_without_a_resident_text(missive):
    lookup_failures.report_dropped_reply("conversation-1", ANSWER)

    [(markdowns, conversation, options)] = posts(missive)
    assert (conversation, options["add_label_list"]) == ("conversation-1", [FAILED_TAG])
    assert markdowns == [
        "Automatic address lookup didn't reply: Missive didn't send the reply (rate limited or rejected). "
        "The resident wasn't texted. Please follow up by hand."
    ]
    missive.reports.send_sms_sync.assert_not_called()


# The SMS queue: dropped replies and the posts that report them.

def ok(body):
    response = requests.Response()
    response.status_code = 201
    return response


def status(code, payload=None):
    response = requests.Response()
    response.status_code = code
    response._content = json.dumps(payload or {}).encode()
    return response


def draft(text, conversation="conversation-1"):
    return {"drafts": {"body": text, "to_fields": [{"phone_number": PHONE}], "conversation": conversation}}


def queued_post(conversation="conversation-1"):
    return MissiveAPI().post_body(["note"], conversation, "Address lookup failed", [FAILED_TAG])


class FakeClock:
    def __init__(self, now=0):
        self.now = now
        self.waits = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


def recorder():
    dropped = []
    return dropped, lambda conversation, role: dropped.append((conversation, role))


@pytest.mark.parametrize("post", [
    lambda body: status(400),
    lambda body: status(429, {"error": {"params": {"retry_after": 31 * 60}}}),
], ids=["rejected", "rate limited past 30 minutes"])
def test_the_queue_reports_a_dropped_answer_once_not_for_each_skipped_follow_up(post):
    dropped, on_dropped = recorder()
    sender = OrderedSender(post, sleep=lambda seconds: None, on_dropped=on_dropped)

    sender.deliver(draft("answer"), queued_at=sender._clock())
    sender.deliver(draft("follow-up"), queued_at=sender._clock(), role=FOLLOW_UP)

    assert dropped == [("conversation-1", ANSWER)]


def test_the_queue_says_which_kind_of_sms_was_dropped():
    dropped, on_dropped = recorder()
    sender = OrderedSender(lambda body: ok(body) if body["drafts"]["body"] == "answer" else status(400),
                           sleep=lambda seconds: None, on_dropped=on_dropped)

    sender.deliver(draft("answer"), queued_at=sender._clock())
    sender.deliver(draft("follow-up"), queued_at=sender._clock(), role=FOLLOW_UP)

    assert dropped == [("conversation-1", FOLLOW_UP)]


def test_the_fallback_text_is_sent_although_the_answer_just_failed_but_follow_ups_are_not():
    sent, dropped = [], []

    def post(body):
        sent.append(body["drafts"]["body"])
        return status(400) if sent[-1] == "answer" else ok(body)

    sender = OrderedSender(post, sleep=lambda seconds: None)
    sender.deliver(draft("answer"), queued_at=sender._clock())
    sender.deliver(draft("follow-up"), queued_at=sender._clock(), role=FOLLOW_UP)
    sender.deliver(draft("lookup error"), queued_at=sender._clock(), role=FALLBACK)

    assert sent == ["answer", "lookup error"]


def test_the_queue_reports_a_reply_that_raised():
    dropped, on_dropped = recorder()

    def network_failure(body):
        raise requests.ConnectionError("no Missive")

    sender = OrderedSender(network_failure, sleep=lambda seconds: None, on_dropped=on_dropped)
    sender.submit(draft("answer"))
    sender.drain_then_report_unsent(timeout=5)

    assert dropped == [("conversation-1", ANSWER)]


def test_a_post_that_raises_does_not_stop_the_sms_queued_after_it(logs):
    sent = []

    def post(body):
        if "posts" in body:
            raise requests.ConnectionError("no Missive")
        sent.append(body["drafts"]["body"])
        return ok(body)

    sender = OrderedSender(post, sleep=lambda seconds: None)
    sender.submit(queued_post())
    sender.submit(draft("answer"))
    sender.drain_then_report_unsent(timeout=5)

    assert sent == ["answer"]
    assert errors_in(logs) == ["Missive sender failed to send a lookup post: ConnectionError"]


def test_a_failing_report_of_a_dropped_reply_is_logged_and_the_queue_keeps_going(logs):
    sent = []

    def post(body):
        sent.append(body["drafts"]["body"])
        return status(400) if body["drafts"]["body"] == "answer" else ok(body)

    def broken_report(conversation, role):
        raise RuntimeError(f"no Missive for {PHONE}")

    sender = OrderedSender(post, sleep=lambda seconds: None, on_dropped=broken_report)
    sender.submit(draft("answer"))
    sender.submit(draft("other conversation", conversation="conversation-2"))
    sender.drain_then_report_unsent(timeout=5)

    assert sent == ["answer", "other conversation"]
    assert "Reporting a dropped lookup SMS failed: RuntimeError" in [record["message"] for record in logs]
    assert PHONE not in " ".join(record["message"] for record in logs)


def test_a_post_is_sent_although_an_sms_of_its_lookup_just_failed():
    sent = []

    def post(body):
        sent.append("post" if "posts" in body else body["drafts"]["body"])
        return status(400) if sent[-1] == "answer" else ok(body)

    sender = OrderedSender(post, sleep=lambda seconds: None)
    sender.deliver(draft("answer"), queued_at=sender._clock())
    sender.deliver(queued_post(), queued_at=sender._clock())

    assert sent == ["answer", "post"]


def errors_in(logs):
    return [record["message"] for record in logs if record["level"].name == "ERROR"]


def test_a_rate_limited_post_waits_out_retry_after_and_is_sent():
    clock, attempts = FakeClock(now=1000), []
    responses = iter([status(429, {"error": {"params": {"retry_after": 60}}}), ok(None)])
    sender = OrderedSender(lambda body: attempts.append(clock()) or next(responses), clock=clock, sleep=clock.sleep)

    sender.deliver(queued_post(), queued_at=clock())

    assert clock.waits == [60]
    assert attempts == [1000, 1060]


def test_a_rejected_post_is_logged_and_not_reported_again(logs):
    dropped, on_dropped = recorder()
    sender = OrderedSender(lambda body: status(400), sleep=lambda seconds: None, on_dropped=on_dropped)

    sender.deliver(queued_post(), queued_at=sender._clock())

    assert dropped == []
    assert errors_in(logs) == ["Missive create post failed with status code 400"]


@pytest.mark.parametrize("queued_ago, retry_after", [(31 * 60, None), (29 * 60, 2 * 60)],
                         ids=["stale before sending", "would wait past 30 minutes"])
def test_a_post_gets_the_same_30_minutes_from_queueing_as_an_sms(logs, queued_ago, retry_after):
    clock, attempts = FakeClock(now=10_000), []
    sender = OrderedSender(
        lambda body: attempts.append(body) or status(429, {"error": {"params": {"retry_after": retry_after}}}),
        clock=clock, sleep=clock.sleep)

    sender.deliver(queued_post(), queued_at=clock() - queued_ago)

    assert len(attempts) == (0 if retry_after is None else 1)
    assert clock.waits == []
    assert errors_in(logs) == ["Dropped a lookup post held up by Missive rate limits"]
    assert_no_resident_data(" ".join(record["message"] for record in logs))


def test_a_slow_post_retry_does_not_make_the_sms_behind_it_miss_its_deadline():
    # Each request takes 25 s. The post's second 429 asks for 870 s, which would put its retry's answer
    # past the 30 minutes of the SMS queued one second after it.
    clock, sent = FakeClock(now=0), []
    post_responses = iter([
        status(429, {"error": {"params": {"retry_after": 880}}}),
        status(429, {"error": {"params": {"retry_after": 870}}}),
        ok(None),
    ])

    def post(body):
        clock.now += 25
        if "posts" in body:
            return next(post_responses)
        sent.append(clock())
        return ok(body)

    sender = OrderedSender(post, clock=clock, sleep=clock.sleep)
    sender.deliver(queued_post(), queued_at=0)
    sender.deliver(draft("answer"), queued_at=1)

    assert clock.waits[0] == 880
    assert len(sent) == 1 and sent[0] - 1 <= 30 * 60


# What a dropped SMS means depends on what it was.

def test_a_dropped_follow_up_is_only_logged(missive, logs):
    lookup_failures.report_dropped_reply("conversation-1", FOLLOW_UP)

    missive.reports.queue_post.assert_not_called()
    missive.reports.send_sms_sync.assert_not_called()
    assert "A follow-up SMS was dropped after its answer went out, conversation conversation-1" in [
        record["message"] for record in logs]


def test_a_dropped_fallback_text_gets_one_unlabeled_note_and_no_new_report(missive):
    lookup_failures.report_dropped_reply("conversation-1", FALLBACK)

    assert posts(missive) == [(
        ["The text telling the resident a reporter will follow up didn't go out. Please reply by hand."],
        "conversation-1",
        {"notification_title": "Address lookup failed"},
    )]
    missive.reports.send_sms_sync.assert_not_called()


def test_a_template_error_while_texting_the_resident_does_not_raise(missive, logs):
    with patch("services.lookup_failures.get_template_content_by_name", side_effect=RuntimeError("cache")):
        lookup_failures.report_lookup_failure("conversation-1", PHONE, lookup_failures.SYSTEM_ERROR, True)

    [(markdowns, _, _)] = posts(missive)
    assert "The resident wasn't texted." in markdowns[0]
    assert errors_in(logs) == ["Texting the resident about a failed lookup failed: RuntimeError"]


# The address parser tells "no address" apart from its own failure only when /search asks it to.

def test_the_address_parser_raises_its_errors_only_when_asked():
    broken = MagicMock()
    broken.complete.side_effect = TimeoutError("OpenAI timed out")
    with patch("helpers.build_llm", return_value=broken):
        assert extract_address_information_with_llm(["hi"]) == (None, None)
        with pytest.raises(TimeoutError):
            extract_address_information_with_llm(["hi"], raise_errors=True)


def test_the_address_parser_still_returns_none_for_text_without_an_address():
    llm = MagicMock()
    llm.complete.return_value = MagicMock(text=json.dumps({"address": None, "sunit": None}))
    with patch("helpers.build_llm", return_value=llm):
        assert extract_address_information_with_llm(["hi"], raise_errors=True) == (None, None)


def test_queued_posts_go_to_the_posts_endpoint_and_drafts_to_drafts(monkeypatch):
    monkeypatch.setenv("MISSIVE_SECRET", "test-secret")
    with patch("libs.MissiveAPI.requests.post") as post:
        post_draft(queued_post())
        post_draft(draft("answer"))

    assert [c.args[0] for c in post.call_args_list] == [CREATE_POST_URL, CREATE_MESSAGE_URL]
    assert all(c.kwargs["timeout"] == 30 for c in post.call_args_list)


def test_queue_post_builds_a_labeled_post_with_its_own_title(monkeypatch):
    monkeypatch.setenv("MISSIVE_SECRET", "test-secret")
    with patch("libs.MissiveAPI.sms_sender") as sms_sender:
        MissiveAPI().queue_post(["note"], "conversation-1", "Address lookup failed", [FAILED_TAG])

    [body] = sms_sender.submit.call_args.args
    assert body["posts"]["conversation"] == "conversation-1"
    assert body["posts"]["notification"]["title"] == "Address lookup failed"
    assert body["posts"]["add_shared_labels"] == [FAILED_TAG]
    assert body["posts"]["attachments"] == [{"markdown": "note", "color": "good"}]


def test_the_weekly_report_post_keeps_its_title_and_has_no_label(monkeypatch):
    monkeypatch.setenv("MISSIVE_SECRET", "test-secret")
    with patch("libs.MissiveAPI.requests.post") as post:
        MissiveAPI().send_post_sync(["report"], "conversation-1")

    body = json.loads(post.call_args.kwargs["data"])["posts"]
    assert body["notification"] == {"title": "Weekly Report", "body": "Summary"}
    assert "add_shared_labels" not in body


# Claims on webhook message ids, so a webhook Missive retries is looked up once.

def test_only_one_of_many_simultaneous_claims_on_a_message_wins(tmp_path):
    start = threading.Barrier(16)
    results = []

    def claim():
        start.wait()
        results.append(claim_webhook("message-1", directory=tmp_path))

    threads = [threading.Thread(target=claim) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [False] * 15 + [True]


def test_claims_in_separate_processes_on_the_same_message_let_one_win(tmp_path):
    script = "import sys; from libs.webhook_claims import claim_webhook; print(claim_webhook('message-1', sys.argv[1]))"
    runs = [subprocess.Popen([sys.executable, "-c", script, str(tmp_path)], cwd=REPO, stdout=subprocess.PIPE,
                             text=True) for _ in range(4)]

    assert sorted(run.communicate(timeout=60)[0].strip() for run in runs) == ["False"] * 3 + ["True"]


def test_an_expired_claim_can_be_claimed_again(tmp_path):
    assert claim_webhook("message-1", directory=tmp_path)
    assert not claim_webhook("message-1", directory=tmp_path)

    later = time.time() + CLAIM_SECONDS + 1
    assert claim_webhook("message-1", directory=tmp_path, clock=lambda: later)
    # The new claim starts its own 15 minutes.
    assert not claim_webhook("message-1", directory=tmp_path)


def test_a_claim_file_name_cannot_be_chosen_by_the_message_id(tmp_path):
    claims = tmp_path / "claims"

    assert claim_webhook("../../escape", directory=claims)

    [claim] = list(claims.iterdir())
    assert len(claim.name) == 64 and not (tmp_path / "escape").exists()


def test_a_message_without_an_id_is_never_claimed(tmp_path):
    assert claim_webhook(None, directory=tmp_path) and claim_webhook(None, directory=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_a_claim_that_cannot_be_checked_lets_the_lookup_run(tmp_path, logs):
    blocked = tmp_path / "file"
    blocked.write_text("")

    assert claim_webhook("message-1", directory=blocked / "claims")
    assert errors_in(logs) == ["Checking for a repeated webhook failed: NotADirectoryError"]


def test_the_sweep_removes_only_expired_claims(tmp_path):
    claim_webhook("old", directory=tmp_path)
    [old] = list(tmp_path.iterdir())
    os.utime(old, (time.time() - CLAIM_SECONDS - 1,) * 2)
    claim_webhook("new", directory=tmp_path)

    sweep_expired_claims(tmp_path)

    assert len(list(tmp_path.iterdir())) == 1 and not old.exists()


# /search itself, in a fresh process as the app runs (main.py sets up Sentry and logging at import).

SEARCH_ROUTE = """
import json, sys, types, uuid
from unittest.mock import MagicMock, patch

import configs.llm
from configs import database

with patch.object(database, "Session") as stub_session:
    stub_session.return_value.query.return_value.filter.return_value.first.return_value = types.SimpleNamespace(
        content="1000"
    )
    import configs.query_engine.text_summary

# A developer's .env may set SENTRY_DNS; this run's errors must not reach the real project.
import configs.sentry
configs.sentry.init_sentry = lambda **options: None

import main
from libs.MissiveAPI import sms_sender
from services import lookup_failures, lookup_retries

# Retries still happen, just without the real waits between them.
lookup_retries.BACKOFF_SECONDS = (0, 0)

lookup_failures.get_template_content_by_name = {"lookup_error": "Sorry, test lookup error text."}.get

webhook = json.load(sys.stdin)
client = main.app.test_client()
results = {"queue_reports_drops": sms_sender.on_dropped is lookup_failures.report_dropped_reply}

def payload_with(message_id):
    # A fresh message id for each lookup, so the repeat check (which outlives this process) never trips.
    message = dict(webhook["message"], id=message_id or str(uuid.uuid4()))
    return dict(webhook, message=message)

def run(name, search=None, payload=None, times=1):
    searches = []

    def counted(**kwargs):
        searches.append(1)
        return search(**kwargs)

    search_patch = patch.object(main, "search_service", side_effect=counted) if search else patch("builtins.id")
    with search_patch, patch.object(lookup_failures, "missive_client") as missive:
        payload = payload or payload_with(None)
        statuses = [client.post("/search", json=payload).status_code for _ in range(times)]
        results[name] = {
            "statuses": statuses,
            "searches": len(searches),
            "posts": [c.args[0] for c in missive.queue_post.call_args_list],
            "sms": [list(c.args) for c in missive.send_sms_sync.call_args_list],
        }

def database_down(**kwargs):
    raise TimeoutError("the database timed out")

def reported_then_raised(**kwargs):
    lookup_failures.report_lookup_failure(kwargs["conversation_id"], kwargs["to_phone"],
                                          lookup_failures.EMPTY_ANSWER, True)
    raise TimeoutError("the database timed out")

def answered(**kwargs):
    return {"result": "answer"}, 200

run("error", database_down)
run("reported then error", reported_then_raised)
run("error after a reported lookup", database_down)
run("no conversation", database_down, payload={"message": {"preview": "hi"}})
run("repeated webhook", answered, payload=payload_with(str(uuid.uuid4())), times=3)
run("repeated failing webhook", database_down, payload=payload_with(str(uuid.uuid4())), times=2)
run("webhooks without a message id", answered, payload={"conversation": webhook["conversation"]}, times=2)

openai_down = MagicMock()
openai_down.complete.side_effect = TimeoutError("OpenAI timed out")
with patch("helpers.build_llm", return_value=openai_down):
    run("address parser error")
results["address parser error"]["parser calls"] = openai_down.complete.call_count
print(json.dumps(results))
"""


@pytest.fixture(scope="module")
def search_route():
    env = {key: value for key, value in os.environ.items() if key != "SENTRY_DNS"}
    env["MISSIVE_LOOKUP_FAILED_TAG_ID"] = FAILED_TAG
    webhook = {"conversation": {"id": "conversation-1"},
               "message": {"from_field": {"id": PHONE}, "preview": RESIDENT_TEXT}}
    app = subprocess.run([sys.executable, "-c", SEARCH_ROUTE], input=json.dumps(webhook), cwd=REPO, env=env,
                         capture_output=True, text=True, timeout=120, check=True)
    # The results line holds the SMS the mock received; everything else the app printed or logged is checked.
    *printed, results = app.stdout.strip().splitlines()
    return json.loads(results), "\n".join(printed) + app.stderr


def test_an_error_in_search_leaves_a_post_and_texts_the_resident(search_route):
    results, _ = search_route

    assert results["error"]["statuses"] == [200]
    assert results["error"]["posts"] == [[
        "Automatic address lookup didn't reply: system error (TimeoutError). "
        f"{ON_ITS_WAY} Please follow up by hand."
    ]]
    assert results["error"]["sms"] == [[LOOKUP_ERROR_SMS, PHONE, "conversation-1"]]


def test_an_address_parser_error_is_reported_as_ours_not_as_unreadable_text(search_route):
    results, _ = search_route

    # Tried three times before the resident hears we had an error (OUT-423).
    assert results["address parser error"]["parser calls"] == 3

    assert results["address parser error"]["posts"] == [[
        "Automatic address lookup didn't reply: system error (TimeoutError). "
        f"{ON_ITS_WAY} Please follow up by hand."
    ]]
    assert results["address parser error"]["sms"] == [[LOOKUP_ERROR_SMS, PHONE, "conversation-1"]]


def test_a_webhook_missive_repeats_is_looked_up_once(search_route):
    results, _ = search_route

    assert results["repeated webhook"]["statuses"] == [200, 200, 200]
    assert results["repeated webhook"]["searches"] == 1
    assert results["repeated failing webhook"]["searches"] == 1
    assert len(results["repeated failing webhook"]["posts"]) == 1
    assert len(results["repeated failing webhook"]["sms"]) == 1


def test_webhooks_without_a_message_id_are_looked_up_every_time(search_route):
    results, _ = search_route

    assert results["webhooks without a message id"]["searches"] == 2


def test_an_error_after_a_reported_failure_is_not_reported_twice(search_route):
    results, _ = search_route

    assert len(results["reported then error"]["posts"]) == 1
    assert len(results["reported then error"]["sms"]) == 1
    # The flag is per request: the next lookup's error is reported again.
    assert len(results["error after a reported lookup"]["posts"]) == 1


def test_an_error_in_a_webhook_without_a_conversation_sends_nothing(search_route):
    results, _ = search_route

    assert results["no conversation"] == {"statuses": [200], "searches": 1, "posts": [], "sms": []}


def test_the_app_has_the_sms_queue_report_dropped_replies(search_route):
    results, _ = search_route

    assert results["queue_reports_drops"] is True


def test_search_errors_log_without_the_resident_text_or_number(search_route):
    _, output = search_route

    assert "Lookup /search failed: TimeoutError" in output
    assert "Skipping a repeated /search webhook for message" in output
    assert_no_resident_data(output)
