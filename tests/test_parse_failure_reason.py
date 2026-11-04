import json
from unittest.mock import MagicMock, patch

import pytest
from loguru import logger

from configs.settings import PARSE_FAILURE_REASONS
from helpers import classify_unparseable_text

RESIDENT_TEXT = "4120 Maple Grove Rd, Southfield MI 48075"


def classify(model_reply):
    with patch("helpers.build_llm") as build_llm:
        build_llm.return_value.complete.return_value = MagicMock(text=model_reply)
        return classify_unparseable_text(RESIDENT_TEXT)


@pytest.mark.parametrize("reason", PARSE_FAILURE_REASONS)
def test_a_listed_reason_is_kept(reason):
    assert classify(json.dumps({"reason": reason})) == reason


def test_a_reason_off_the_list_becomes_unknown():
    assert classify(json.dumps({"reason": "Southfield is not in Detroit"})) == "unknown"


def test_a_reply_that_is_not_json_becomes_unknown():
    assert classify("The resident sent an address in Southfield") == "unknown"


def test_a_reply_without_a_reason_becomes_unknown():
    assert classify(json.dumps(["outside_detroit"])) == "unknown"


def test_a_failed_model_call_becomes_unknown():
    with patch("helpers.build_llm") as build_llm:
        build_llm.return_value.complete.side_effect = RuntimeError(f"model refused: {RESIDENT_TEXT}")
        assert classify_unparseable_text(RESIDENT_TEXT) == "unknown"


def test_a_failed_model_call_logs_the_error_type_only():
    records = []
    sink = logger.add(lambda message: records.append(message.record), level="DEBUG")
    try:
        with patch("helpers.build_llm") as build_llm:
            build_llm.return_value.complete.side_effect = RuntimeError(f"model refused: {RESIDENT_TEXT}")
            classify_unparseable_text(RESIDENT_TEXT)
    finally:
        logger.remove(sink)

    assert [record["message"] for record in records] == ["Classifying a parse failure failed: RuntimeError"]
