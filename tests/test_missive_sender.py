import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.loguru import LoggingLevels, LoguruIntegration

from libs.MissiveAPI import MissiveAPI, post_draft, sms_sender
from libs.missive_sender import OrderedSender

QUARTER_HOUR = 15 * 60
PHONE = "+15550001234"
RESIDENT_TEXT = "We don't have info for 1111 E. Jefferson"
REPO = Path(__file__).resolve().parents[1]


class FakeClock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def missive_response(status_code, payload=None, headers=None):
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(payload or {}).encode()
    response.headers.update(headers or {})
    return response


def rate_limited(retry_after):
    return missive_response(429, {"error": {"params": {"retry_after": retry_after}}})


class FakeMissive:
    """Missive's 900-per-15-minutes window, which a broadcast keeps drained until `busy_until`.

    Like the real API, the window resets on the quarter hour and `retry_after` counts down to it.
    """

    def __init__(self, clock, busy_until=0, retry_after_in="body"):
        self.clock = clock
        self.busy_until = busy_until
        self.retry_after_in = retry_after_in
        self.sent = []

    def post(self, body):
        now = self.clock()
        if now < self.busy_until:
            retry_after = int((now // QUARTER_HOUR + 1) * QUARTER_HOUR + 1 - now)
            if self.retry_after_in == "body":
                return rate_limited(retry_after)
            return missive_response(429, {"error": {"message": "Too many requests."}},
                                    {"Retry-After": str(retry_after)})
        self.sent.append((now, body["drafts"]["body"]))
        return missive_response(201)


def draft(text, conversation="conversation-1"):
    return {"drafts": {"body": text, "to_fields": [{"phone_number": PHONE}], "conversation": conversation}}


def rate_limited_until(busy_until, retry_after_in="body"):
    clock = FakeClock(now=5 * QUARTER_HOUR + 564)
    missive = FakeMissive(clock, busy_until=busy_until, retry_after_in=retry_after_in)
    return clock, missive, OrderedSender(missive.post, clock=clock, sleep=clock.sleep)


def wait_for(condition, timeout=5):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.05)


def assert_leaves_out_the_resident_and_token(logs):
    logged = " ".join(record["message"] for record in logs)
    assert logged
    assert PHONE not in logged and "Jefferson" not in logged and "secret-token" not in logged
    assert all(record["exception"] is None for record in logs)


def errors(logs):
    return [record["message"] for record in logs if record["level"].name == "ERROR"]


@pytest.fixture
def logs():
    records = []
    sink = logger.add(lambda message: records.append(message.record), level="DEBUG")
    yield records
    logger.remove(sink)


@pytest.mark.parametrize("busy_until, retry_after_in", [
    (6 * QUARTER_HOUR, "body"),
    (6 * QUARTER_HOUR, "header"),
    (7 * QUARTER_HOUR, "body"),
], ids=["next window", "retry-after header", "window after next"])
def test_reply_is_sent_as_soon_as_the_rate_limit_window_resets(busy_until, retry_after_in):
    clock, missive, sender = rate_limited_until(busy_until, retry_after_in)

    sender.deliver(draft("answer"), queued_at=clock())

    assert missive.sent == [(busy_until + 1, "answer")]


def test_reply_that_would_go_out_after_30_minutes_is_dropped_instead():
    clock, missive, sender = rate_limited_until(8 * QUARTER_HOUR)

    sender.deliver(draft("answer"), queued_at=clock())

    assert missive.sent == []


@pytest.mark.parametrize("retry_after, expected", [
    (29 * 60 + 59, ("sent", [29 * 60 + 59])),
    (30 * 60 + 1, ("dropped", [])),
], ids=["29:59", "30:01"])
def test_the_30_minute_limit_is_checked_before_waiting(retry_after, expected):
    clock = FakeClock(now=0)
    waits = []
    responses = [rate_limited(retry_after), missive_response(201)]

    def sleep(seconds):
        waits.append(seconds)
        clock.sleep(seconds)

    OrderedSender(lambda body: responses.pop(0), clock=clock, sleep=sleep).deliver(draft("answer"), queued_at=0)

    assert ("sent" if not responses else "dropped", waits) == expected


def test_reply_that_waited_behind_others_for_30_minutes_is_dropped_without_a_send():
    clock, missive, sender = rate_limited_until(0)

    sender.deliver(draft("follow-up"), queued_at=clock() - 31 * 60)

    assert missive.sent == []


def test_the_30_minutes_count_from_when_the_reply_was_queued():
    clock = FakeClock(now=0)
    sent = []
    attempts = []

    def post(body):
        text = body["drafts"]["body"]
        attempts.append(text)
        if text == "first conversation" and clock() < 25 * 60:
            return rate_limited(25 * 60 - clock())
        if attempts.count("second conversation") == 1:
            return rate_limited(10 * 60)
        sent.append(text)
        return missive_response(201)

    sender = OrderedSender(post, clock=clock, sleep=clock.sleep)
    sender.submit(draft("first conversation"))
    sender.submit(draft("second conversation", conversation="conversation-2"))
    sender.drain_then_report_unsent(timeout=5)

    assert sent == ["first conversation"]


def test_follow_up_is_dropped_when_its_answer_was():
    clock = FakeClock(now=1700)
    missive = FakeMissive(clock, busy_until=2 * QUARTER_HOUR + 1)
    sender = OrderedSender(missive.post, clock=clock, sleep=clock.sleep)

    sender.deliver(draft("answer"), queued_at=0)
    sender.deliver(draft("follow-up"), queued_at=2)

    assert missive.sent == []


def test_a_resident_retry_is_still_sent_after_their_first_lookup_was_dropped():
    clock = FakeClock(now=1700)
    missive = FakeMissive(clock, busy_until=2 * QUARTER_HOUR + 1)
    sender = OrderedSender(missive.post, clock=clock, sleep=clock.sleep)

    sender.deliver(draft("answer"), queued_at=0)
    sender.deliver(draft("retry answer"), queued_at=84)

    assert missive.sent == [(2 * QUARTER_HOUR + 1, "retry answer")]


def test_a_dropped_reply_does_not_hold_back_other_conversations():
    clock = FakeClock(now=1700)
    missive = FakeMissive(clock, busy_until=2 * QUARTER_HOUR + 1)
    sender = OrderedSender(missive.post, clock=clock, sleep=clock.sleep)

    sender.deliver(draft("answer"), queued_at=0)
    sender.deliver(draft("other answer", conversation="conversation-2"), queued_at=2)

    assert missive.sent == [(2 * QUARTER_HOUR + 1, "other answer")]


def test_dropping_a_reply_logs_one_fixed_error_for_sentry_to_group(logs):
    clock, _, sender = rate_limited_until(9 * QUARTER_HOUR)

    sender.deliver(draft("answer"), queued_at=clock())
    sender.deliver(draft("follow-up", conversation="conversation-2"), queued_at=clock() - 31 * 60)

    assert errors(logs) == ["Dropped a lookup SMS held up by Missive rate limits"] * 2


def test_rate_limit_logs_leave_out_the_phone_number_and_message(logs):
    clock, _, sender = rate_limited_until(9 * QUARTER_HOUR)

    sender.deliver(draft(RESIDENT_TEXT), queued_at=clock())

    assert_leaves_out_the_resident_and_token(logs)


def test_follow_up_goes_out_two_seconds_after_the_answer():
    clock, missive, sender = rate_limited_until(0)

    sender.deliver(draft("answer"), queued_at=clock())
    sender.deliver(draft("follow-up"), queued_at=clock())

    (answer_at, _), (follow_up_at, _) = missive.sent
    assert follow_up_at - answer_at == 2


def test_a_zero_retry_after_still_waits_a_second():
    waits = []
    responses = [rate_limited(0), missive_response(201)]
    sender = OrderedSender(lambda body: responses.pop(0), clock=FakeClock(now=0), sleep=waits.append)

    sender.deliver(draft("answer"), queued_at=0)

    assert waits[0] == 1


def rejecting_post(body):
    return missive_response(400, {"error": {"message": "Invalid phone number"}})


def test_other_failures_are_not_retried():
    attempts = []
    sender = OrderedSender(lambda body: attempts.append(body) or rejecting_post(body),
                           clock=FakeClock(now=0), sleep=lambda seconds: None)

    sender.deliver(draft("answer"), queued_at=0)

    assert len(attempts) == 1


def test_other_failures_log_the_status_code_without_the_phone_number_and_message(logs):
    sender = OrderedSender(rejecting_post, clock=FakeClock(now=0), sleep=lambda seconds: None)

    sender.deliver(draft(RESIDENT_TEXT), queued_at=0)

    assert errors(logs) == ["Missive send message failed with status code 400"]
    assert_leaves_out_the_resident_and_token(logs)


def network_failure(body):
    headers = {"Authorization": "Bearer secret-token"}
    raise requests.ConnectionError(f"could not reach Missive with {headers} and {body}")


@pytest.mark.parametrize("fail", [rejecting_post, network_failure], ids=["rejected", "network error"])
def test_after_a_failed_answer_its_follow_up_is_skipped_but_other_conversations_are_sent(fail):
    attempts = []

    def post(body):
        text = body["drafts"]["body"]
        attempts.append(text)
        return fail(body) if text == "answer" else missive_response(201)

    sender = OrderedSender(post, sleep=lambda seconds: None)
    sender.submit(draft("answer"))
    sender.submit(draft("follow-up"))
    sender.submit(draft("other conversation", conversation="conversation-2"))
    sender.drain_then_report_unsent(timeout=5)

    assert attempts == ["answer", "other conversation"]


def test_follow_up_waits_until_the_rate_limited_answer_is_sent():
    attempts = []
    answer_waiting = threading.Event()
    release = threading.Event()

    def post(body):
        attempts.append(body["drafts"]["body"])
        return rate_limited(30) if attempts == ["answer"] else missive_response(201)

    def sleep(seconds):
        if seconds == 30:
            answer_waiting.set()
            release.wait(timeout=5)

    sender = OrderedSender(post, sleep=sleep)
    sender.submit(draft("answer"))
    sender.submit(draft("follow-up"))
    assert answer_waiting.wait(timeout=5)
    attempts_while_answer_waits = list(attempts)
    release.set()
    wait_for(lambda: len(attempts) == 3)

    assert (attempts_while_answer_waits, attempts) == (["answer"], ["answer", "answer", "follow-up"])


def test_submit_returns_while_missive_is_still_answering():
    release = threading.Event()
    sent = threading.Event()

    def slow_post(body):
        release.wait(timeout=5)
        sent.set()
        return missive_response(201)

    sender = OrderedSender(slow_post, sleep=lambda seconds: None)

    sender.submit(draft("answer"))
    returned_before_missive_answered = not sent.is_set()
    release.set()

    assert returned_before_missive_answered and sent.wait(timeout=5)


def test_errors_are_logged_by_type_only(logs):
    sender = OrderedSender(network_failure, sleep=lambda seconds: None)

    sender.submit(draft(RESIDENT_TEXT))
    sender.drain_then_report_unsent(timeout=5)

    assert errors(logs) == ["Missive sender failed to send a lookup SMS: ConnectionError"]
    assert_leaves_out_the_resident_and_token(logs)


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_a_forked_worker_still_sends_after_the_parent_started_sending():
    sent = threading.Event()
    sender = OrderedSender(lambda body: sent.set() or missive_response(201), sleep=lambda seconds: None)
    sender.submit(draft("from the parent"))
    assert sent.wait(timeout=5)
    sent.clear()

    pid = os.fork()
    if pid == 0:
        sent_from_child = False
        try:
            sender.submit(draft("from the forked worker"))
            sent_from_child = sent.wait(timeout=5)
        finally:
            os._exit(0 if sent_from_child else 1)

    assert child_exit_code(pid, timeout=10) == 0


def child_exit_code(pid, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        finished, status = os.waitpid(pid, os.WNOHANG)
        if finished:
            return os.waitstatus_to_exitcode(status)
        time.sleep(0.1)
    os.kill(pid, 9)
    os.waitpid(pid, 0)
    raise AssertionError("the forked worker hung")


def test_send_sms_sync_queues_the_same_draft_it_used_to_post(monkeypatch):
    monkeypatch.setenv("MISSIVE_SECRET", "test-secret")
    missive = MissiveAPI()
    with patch("libs.MissiveAPI.sms_sender") as sms_sender:
        missive.send_sms_sync("answer", PHONE, conversation_id="conversation-1", add_label_list=["lookup"])

    sms_sender.submit.assert_called_once_with({
        "drafts": {
            "body": "answer",
            "from_field": {"phone_number": missive.phone_number},
            "organization": missive.organization,
            "to_fields": [{"phone_number": PHONE}],
            "add_shared_labels": ["lookup"],
            "remove_shared_labels": [],
            "send": True,
            "conversation": "conversation-1",
        },
    })


def test_drafts_are_posted_with_the_token_and_a_timeout(monkeypatch):
    monkeypatch.setenv("MISSIVE_SECRET", "test-secret")
    with patch("libs.MissiveAPI.requests.post") as post:
        post_draft(draft("answer"))

    assert (post.call_args.kwargs["headers"]["Authorization"], post.call_args.kwargs["timeout"]) == (
        "Bearer test-secret", 30
    )


def test_send_sms_sync_reaches_missive_through_the_shared_sender(monkeypatch):
    monkeypatch.setenv("MISSIVE_SECRET", "test-secret")
    with patch("libs.MissiveAPI.requests.post", return_value=missive_response(201)) as post:
        MissiveAPI().send_sms_sync("answer", PHONE, conversation_id="conversation-1")
        sms_sender.drain_then_report_unsent(timeout=5)

    assert json.loads(post.call_args.kwargs["data"])["drafts"]["body"] == "answer"


EXITING_WORKER = """
import threading
from libs.missive_sender import OrderedSender

stuck = threading.Event()
sender = OrderedSender(lambda body: stuck.wait())
sender.submit({"drafts": {"body": "answer", "conversation": "conversation-1"}})
"""


def test_a_worker_exiting_with_a_stuck_reply_reports_it_before_docker_would_kill_it():
    started = time.monotonic()
    worker = subprocess.run([sys.executable, "-c", EXITING_WORKER], cwd=REPO, capture_output=True, text=True,
                            timeout=15)

    assert time.monotonic() - started < 9
    assert "Worker exited with lookup SMS still queued for Missive" in worker.stderr


def test_exiting_worker_sends_replies_already_in_flight_and_exits_quietly(logs):
    sent = []

    def slow_post(body):
        time.sleep(0.3)
        sent.append(body["drafts"]["body"])
        return missive_response(201)

    sender = OrderedSender(slow_post, sleep=lambda seconds: None)
    sender.submit(draft("answer"))
    sender.submit(draft("follow-up"))

    sender.drain_then_report_unsent(timeout=5)

    assert sent == ["answer", "follow-up"] and logs == []


def test_exiting_worker_reports_replies_it_could_not_send_in_time(logs):
    release = threading.Event()

    def stuck_post(body):
        release.wait(timeout=5)
        return missive_response(201)

    sender = OrderedSender(stuck_post, sleep=lambda seconds: None)
    sender.submit(draft("answer"))
    sender.submit(draft("follow-up"))

    sender.drain_then_report_unsent(timeout=0.3)
    release.set()

    assert [record["message"] for record in logs] == [
        "Worker exiting with 2 lookup SMS not yet sent to Missive",
        "Worker exited with lookup SMS still queued for Missive",
    ]


@pytest.fixture
def sentry_events():
    # Same integrations as main.py, which keeps Sentry's defaults (threading among them).
    events = []
    sentry_sdk.init(
        dsn="http://public@127.0.0.1:1/1",
        enable_tracing=True,
        integrations=[LoguruIntegration(level=LoggingLevels.INFO.value, event_level=LoggingLevels.ERROR.value)],
        before_send=lambda event, hint: events.append(event),
    )
    yield events
    sentry_sdk.init()


def test_sentry_events_carry_the_breadcrumbs_of_the_request_that_queued_the_sms(sentry_events):
    sender = OrderedSender(rejecting_post, sleep=lambda seconds: None)
    with sentry_sdk.isolation_scope():
        logger.info("first request")
        sender.submit(draft("answer"))
    with sentry_sdk.isolation_scope():
        logger.info("second request")
        sender.submit(draft("answer", conversation="conversation-2"))

    wait_for(lambda: len(sentry_events) == 2)
    second_request_crumbs = " ".join(crumb["message"] for crumb in sentry_events[1]["breadcrumbs"]["values"])
    assert "second request" in second_request_crumbs and "first request" not in second_request_crumbs
