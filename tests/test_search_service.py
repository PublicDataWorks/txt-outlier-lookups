import sys
import types
from unittest.mock import MagicMock, patch

import pytest
import sentry_sdk
from loguru import logger

# text_summary reads max_tokens from the database at import and exits without it. search_service
# doesn't summarise anything, so these tests stand it in rather than depend on database contents.
sys.modules.setdefault("configs.query_engine.text_summary", types.SimpleNamespace(generate_text_summary=None))

from services.services import search_service  # noqa: E402

PHONE = "+15550001234"


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


def search_unparseable(query, conversation_id="conversation-1"):
    with patch("services.services.extract_address_information_with_llm", return_value=(None, None)), \
            patch("services.services.Session", MagicMock()):
        return search_service(query=query, conversation_id=conversation_id, to_phone=PHONE)


def test_unparseable_text_gets_the_same_response():
    assert search_unparseable("1") == ({"message": "Couldn't parse address from query"}, 200)


def test_unparseable_text_is_not_logged_as_an_error(logs):
    search_unparseable("26184 Princeton St. Inkster")

    assert [record for record in logs if record["level"].name == "ERROR"] == []


def test_parse_failure_logs_leave_out_the_text_and_phone_number(logs):
    search_unparseable("26184 Princeton St. Inkster")

    failure_logs = " ".join(record["message"] for record in logs if "parse" in record["message"])
    assert failure_logs and "Princeton" not in failure_logs and PHONE not in failure_logs


def test_every_parse_failure_lands_in_one_sentry_issue(sentry_events):
    search_unparseable("26184 Princeton St. Inkster", conversation_id="conversation-1")
    search_unparseable("313-555-0100 Joe", conversation_id="conversation-2")

    assert [(event["level"], event["fingerprint"], event["message"]) for event in sentry_events] == [
        ("warning", ["lookup-parse-failure"], "Couldn't parse an address from a lookup text"),
    ] * 2
