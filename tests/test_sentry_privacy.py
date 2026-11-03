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
# would decide the format here. Each run gets a fresh process, as the app does. A capturing transport
# stands in for Sentry so that the app's own before_send hooks still run.
CAPTURE_SENTRY = """
import json, sys
from sentry_sdk.transport import Transport
import configs.sentry

sent = []

class Capture(Transport):
    def capture_envelope(self, envelope):
        sent.extend(item.payload.json for item in envelope.items if item.type in ("event", "transaction"))

# main.py calls init_sentry() itself, so every call gets the capturing transport.
real_init_sentry = configs.sentry.init_sentry
configs.sentry.init_sentry = lambda **options: real_init_sentry(transport=Capture, **options)
"""

LOGGED_EXCEPTION_IN_A_WEBHOOK = CAPTURE_SENTRY + """
from flask import Flask, request
configs.sentry.init_sentry()
from loguru import logger

app = Flask(__name__)

@app.route("/search", methods=["POST"])
def search():
    to_phone = request.get_json()["message"]["from_field"]["id"]
    try:
        raise ValueError("lookup failed")
    except ValueError:
        logger.exception(f"Lookup failed for a {len(to_phone)} character number")
    return "", 200

app.test_client().post("/search", json=json.load(sys.stdin))
print(json.dumps([event for event in sent if event.get("type") != "transaction"], default=str))
"""

IMPORT_THE_APP = """
import json, sys, types
from unittest.mock import patch

import configs.llm
from configs import database

# text_summary reads max_tokens from the database at import.
with patch.object(database, "Session") as stub_session:
    stub_session.return_value.query.return_value.filter.return_value.first.return_value = types.SimpleNamespace(
        content="1000"
    )
    import configs.query_engine.text_summary

import main
"""

SIDEBAR_REQUESTS_TO_THE_APP = CAPTURE_SENTRY + IMPORT_THE_APP + """
phone = json.load(sys.stdin)["message"]["from_field"]["id"]
client = main.app.test_client()
with patch.object(main, "get_conversation_data", side_effect=RuntimeError(f"no summary for {phone}")):
    client.get(f"/conversations/conversation-1?reference={phone[1:]}")
with patch.object(main, "update_author_and_missive", side_effect=RuntimeError("update failed")):
    client.patch(f"/contacts/%2B{phone[1:]}", json={"zipcode": "48207"})
print(json.dumps(sent, default=str))
"""


def run_with_sentry(script):
    return subprocess.run([sys.executable, "-c", script], input=json.dumps(WEBHOOK), cwd=REPO,
                          env={**os.environ, "SENTRY_DNS": "http://public@127.0.0.1:1/1"},
                          capture_output=True, text=True, timeout=60, check=True)


def sentry_payloads(script):
    return json.loads(run_with_sentry(script).stdout.strip().splitlines()[-1])


def assert_no_resident_data(payloads):
    sent = json.dumps(payloads)
    assert payloads and PHONE[2:] not in sent and "Jefferson" not in sent


def test_sentry_events_from_a_webhook_leave_out_the_phone_number_and_text():
    assert_no_resident_data(sentry_payloads(LOGGED_EXCEPTION_IN_A_WEBHOOK))


def test_sentry_events_keep_the_exception_and_the_logged_text_alone():
    [event] = sentry_payloads(LOGGED_EXCEPTION_IN_A_WEBHOOK)

    assert (event["logentry"]["message"], event["exception"]["values"][0]["type"]) == (
        "Lookup failed for a 12 character number", "ValueError"
    )


def test_sidebar_requests_send_no_phone_number_to_sentry_in_urls_breadcrumbs_or_errors():
    payloads = sentry_payloads(SIDEBAR_REQUESTS_TO_THE_APP)

    assert {payload.get("type", "error") for payload in payloads} == {"error", "transaction"}
    assert_no_resident_data(payloads)


def test_sidebar_errors_keep_their_traceback_in_the_container_log():
    app = run_with_sentry(SIDEBAR_REQUESTS_TO_THE_APP)

    assert "in get_conversation" in app.stdout and "RuntimeError" in app.stdout


A_LOGGED_EXCEPTION_IN_THE_APP = IMPORT_THE_APP + """
from loguru import logger

def look_up(to_phone):
    try:
        raise ValueError(f"lookup failed after {len(to_phone)} characters")
    except ValueError:
        logger.exception("Lookup failed")

logger.info("Lookup started")
look_up(json.load(sys.stdin)["message"]["from_field"]["id"])
"""


def app_stderr(script, directory):
    # Run from a file: loguru only annotates variables when it can read the source lines.
    app_file = directory / "app.py"
    app_file.write_text(f"import sys\nsys.path.insert(0, {str(REPO)!r})\n{script}")
    env = {key: value for key, value in os.environ.items() if key != "SENTRY_DNS"}
    app = subprocess.run([sys.executable, str(app_file)], input=json.dumps(WEBHOOK), cwd=REPO, env=env,
                         capture_output=True, text=True, timeout=60, check=True)
    return app.stderr


def test_the_container_log_shows_tracebacks_without_variable_values(tmp_path):
    log = app_stderr(A_LOGGED_EXCEPTION_IN_THE_APP, tmp_path)

    assert "ValueError: lookup failed" in log and PHONE[2:] not in log


def test_the_container_log_prints_each_line_once_with_its_code_location(tmp_path):
    log = app_stderr(A_LOGGED_EXCEPTION_IN_THE_APP, tmp_path)

    [started] = [line for line in log.splitlines() if "Lookup started" in line]
    assert "INFO __main__:<module>:" in started


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
