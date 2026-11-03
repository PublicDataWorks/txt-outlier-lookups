import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
from loguru import logger

from helpers import extract_address_information_with_llm
from libs.MissiveAPI import MissiveAPI

PHONE = "+15550001234"
RESIDENT_TEXT = "1111 E. Jefferson, my landlord won't fix the heat"
WEBHOOK = {"conversation": {"id": "conversation-1"},
           "message": {"from_field": {"id": PHONE}, "preview": RESIDENT_TEXT}}
REPO = Path(__file__).resolve().parents[1]

# Sentry's loguru integration installs its handlers once per process, so another test's Sentry setup
# would decide the format here. Each run gets a fresh process, as the app does.
APP_IN_A_FRESH_PROCESS = """
import json, sys
from flask import Flask, request
from loguru import logger
from configs.sentry import init_sentry

events = []
init_sentry(before_send=lambda event, hint: events.append(event))
app = Flask(__name__)

@app.route("/search", methods=["POST"])
def search():
    to_phone = request.get_json()["message"]["from_field"]["id"]
    logger.info(f"Lookup started for conversation {request.get_json()['conversation']['id']}")
    try:
        raise ValueError("lookup failed")
    except ValueError:
        logger.exception(f"Lookup failed for a {len(to_phone)} character number")
    return "", 200

app.test_client().post("/search", json=json.load(sys.stdin))
print(json.dumps(events, default=str))
"""


def sentry_events_for_a_failing_webhook():
    app = subprocess.run([sys.executable, "-c", APP_IN_A_FRESH_PROCESS], input=json.dumps(WEBHOOK), cwd=REPO,
                         env={**os.environ, "SENTRY_DNS": "http://public@127.0.0.1:1/1"},
                         capture_output=True, text=True, timeout=60, check=True)
    return json.loads(app.stdout.strip().splitlines()[-1])


def test_sentry_events_from_a_webhook_leave_out_the_phone_number_and_text():
    events = sentry_events_for_a_failing_webhook()

    sent = json.dumps(events)
    assert events and PHONE not in sent and "Jefferson" not in sent


def test_sentry_events_keep_the_exception_and_the_logged_text_alone():
    [event] = sentry_events_for_a_failing_webhook()

    assert (event["logentry"]["message"], event["exception"]["values"][0]["type"]) == (
        "Lookup failed for a 12 character number", "ValueError"
    )


@pytest.fixture
def logs():
    records = []
    sink = logger.add(lambda message: records.append(message.record), level="DEBUG")
    yield records
    logger.remove(sink)


def test_address_parser_failures_log_the_error_type_only(logs):
    with patch("helpers.build_llm") as build_llm:
        build_llm.return_value.complete.side_effect = RuntimeError(f"model refused: {RESIDENT_TEXT}")
        extract_address_information_with_llm([RESIDENT_TEXT])

    assert [record["message"] for record in logs] == ["The address parser failed: RuntimeError"]


def test_address_parser_success_logs_leave_out_the_address(logs):
    with patch("helpers.build_llm") as build_llm:
        build_llm.return_value.complete.return_value = MagicMock(
            text=json.dumps({"address": "1111 E Jefferson Ave", "sunit": None}))
        extract_address_information_with_llm([RESIDENT_TEXT])

    assert "Jefferson" not in " ".join(record["message"] for record in logs)


def test_failed_missive_posts_log_the_status_code_only(logs, monkeypatch):
    monkeypatch.setenv("MISSIVE_SECRET", "test-secret")
    rejected = requests.Response()
    rejected.status_code = 400
    rejected._content = json.dumps({"error": RESIDENT_TEXT}).encode()
    with patch("libs.MissiveAPI.requests.post", return_value=rejected):
        MissiveAPI().send_post_sync([f"Resident said: {RESIDENT_TEXT}"], "conversation-1")

    assert [record["message"] for record in logs] == ["Create Missive post failed with status code 400"]
