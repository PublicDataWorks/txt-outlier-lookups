import json
import os
import threading
from unittest.mock import patch

import pytest
import requests
import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.loguru import LoggingLevels, LoguruIntegration

from libs.MissiveAPI import MissiveAPI
from libs.missive_sender import OrderedSender

QUARTER_HOUR = 15 * 60
PHONE = "+15550001234"


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


class FakeMissive:
    """Missive's 900-per-15-minutes window, which a broadcast keeps drained until `busy_until`.

    Like the real API, the window resets on the quarter hour and `retry_after` counts down to it.
    """

    def __init__(self, clock, busy_until=0, retry_after_in="body"):
        self.clock = clock
        self.busy_until = busy_until
        self.retry_after_in = retry_after_in
        self.sent = []
        self.attempts = 0
        self.all_sent = threading.Event()
        self.expected = 1

    def post(self, body):
        self.attempts += 1
        now = self.clock()
        if now < self.busy_until:
            retry_after = int((now // QUARTER_HOUR + 1) * QUARTER_HOUR + 1 - now)
            if self.retry_after_in == "body":
                payload = {"error": {"message": "Too many requests. Please try again shortly.",
                                     "params": {"retry_after": retry_after}}}
                return missive_response(429, payload)
            return missive_response(429, {"error": {"message": "Too many requests."}},
                                    {"Retry-After": str(retry_after)})
        self.sent.append((now, body["drafts"]["body"]))
        if len(self.sent) >= self.expected:
            self.all_sent.set()
        return missive_response(201, {"drafts": {"id": "draft"}})


def draft(text):
    return {"drafts": {"body": text, "to_fields": [{"phone_number": PHONE}], "conversation": "conversation-1"}}


@pytest.fixture
def logs():
    records = []
    sink = logger.add(lambda message: records.append(message.record), level="DEBUG")
    yield records
    logger.remove(sink)


def test_reply_is_sent_once_the_rate_limit_window_resets():
    clock = FakeClock(now=5 * QUARTER_HOUR + 564)
    missive = FakeMissive(clock, busy_until=6 * QUARTER_HOUR)
    sender = OrderedSender(missive.post, clock=clock, sleep=clock.sleep)

    sender.deliver(draft("answer"), queued_at=clock())

    assert missive.sent == [(6 * QUARTER_HOUR + 1, "answer")]


def test_retry_after_header_is_used_when_the_body_has_none():
    clock = FakeClock(now=5 * QUARTER_HOUR + 564)
    missive = FakeMissive(clock, busy_until=6 * QUARTER_HOUR, retry_after_in="header")
    sender = OrderedSender(missive.post, clock=clock, sleep=clock.sleep)

    sender.deliver(draft("answer"), queued_at=clock())

    assert missive.sent == [(6 * QUARTER_HOUR + 1, "answer")]


def test_reply_still_rate_limited_after_two_windows_is_dropped():
    clock = FakeClock(now=5 * QUARTER_HOUR + 564)
    missive = FakeMissive(clock, busy_until=9 * QUARTER_HOUR)
    sender = OrderedSender(missive.post, clock=clock, sleep=clock.sleep)

    sender.deliver(draft("answer"), queued_at=clock())

    assert missive.sent == []


def test_reply_that_waited_out_a_drained_window_is_still_sent_within_two_windows():
    clock = FakeClock(now=5 * QUARTER_HOUR + 564)
    missive = FakeMissive(clock, busy_until=7 * QUARTER_HOUR)
    sender = OrderedSender(missive.post, clock=clock, sleep=clock.sleep)

    sender.deliver(draft("answer"), queued_at=clock())

    assert missive.sent == [(7 * QUARTER_HOUR + 1, "answer")]


def test_dropping_a_reply_logs_one_fixed_error_for_sentry_to_group(logs):
    clock = FakeClock(now=5 * QUARTER_HOUR + 564)
    sender = OrderedSender(FakeMissive(clock, busy_until=9 * QUARTER_HOUR).post, clock=clock, sleep=clock.sleep)

    sender.deliver(draft("answer"), queued_at=clock())

    assert [record["message"] for record in logs if record["level"].name == "ERROR"] == [
        "Dropped a lookup SMS: Missive kept rate limiting it for 30 minutes"
    ]


def test_rate_limit_logs_leave_out_the_phone_number_and_message(logs):
    clock = FakeClock(now=5 * QUARTER_HOUR + 564)
    sender = OrderedSender(FakeMissive(clock, busy_until=9 * QUARTER_HOUR).post, clock=clock, sleep=clock.sleep)

    sender.deliver(draft("We don't have info for 1111 E. Jefferson"), queued_at=clock())

    logged = " ".join(record["message"] for record in logs)
    assert PHONE not in logged and "Jefferson" not in logged


def test_other_failures_are_not_retried():
    attempts = []

    def post(body):
        attempts.append(body)
        return missive_response(400, {"error": {"message": "Invalid phone number"}})

    OrderedSender(post).deliver(draft("answer"), queued_at=0)

    assert len(attempts) == 1


def test_other_failures_log_the_status_without_the_draft(logs):
    def post(body):
        return missive_response(400, {"error": {"message": "Invalid phone number"}})

    OrderedSender(post).deliver(draft("answer"), queued_at=0)

    assert [record["message"] for record in logs if record["level"].name == "ERROR"] == [
        "Missive send message failed with status code 400"
    ]


def test_follow_up_queued_behind_a_rate_limited_answer_is_sent_after_it():
    clock = FakeClock(now=5 * QUARTER_HOUR + 564)
    missive = FakeMissive(clock, busy_until=6 * QUARTER_HOUR)
    missive.expected = 2
    sender = OrderedSender(missive.post, clock=clock, sleep=clock.sleep)

    sender.submit(draft("answer"))
    sender.submit(draft("follow-up"))

    assert missive.all_sent.wait(timeout=5)
    assert [text for _, text in missive.sent] == ["answer", "follow-up"]


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


def test_a_network_error_does_not_stop_later_messages():
    sent = []
    done = threading.Event()

    def flaky_post(body):
        if body["drafts"]["body"] == "answer":
            raise requests.ConnectionError("connection reset")
        sent.append(body["drafts"]["body"])
        done.set()
        return missive_response(201)

    sender = OrderedSender(flaky_post, sleep=lambda seconds: None)

    sender.submit(draft("answer"))
    sender.submit(draft("follow-up"))

    assert done.wait(timeout=5) and sent == ["follow-up"]


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_a_forked_worker_still_sends_after_the_parent_started_sending():
    sent = threading.Event()
    sender = OrderedSender(lambda body: sent.set() or missive_response(201), sleep=lambda seconds: None)
    sender.submit(draft("from the parent"))
    assert sent.wait(timeout=5)
    sent.clear()
    wait_until_everything_is_sent(sender)

    pid = os.fork()
    if pid == 0:
        sent_from_child = False
        try:
            sender.submit(draft("from the forked worker"))
            sent_from_child = sent.wait(timeout=5)
        finally:
            os._exit(0 if sent_from_child else 1)

    assert child_exit_code(pid, timeout=10) == 0


def wait_until_everything_is_sent(sender):
    # A fork while the sending thread holds its lock would leave the child blocked on that lock.
    with patch("libs.missive_sender.logger") as quiet_logger:
        for _ in range(50):
            quiet_logger.reset_mock()
            sender.report_unsent()
            if not quiet_logger.method_calls:
                return
            threading.Event().wait(0.1)
    raise AssertionError("the parent's sender never finished")


def child_exit_code(pid, timeout):
    for _ in range(timeout * 10):
        finished, status = os.waitpid(pid, os.WNOHANG)
        if finished:
            return os.waitstatus_to_exitcode(status)
        threading.Event().wait(0.1)
    os.kill(pid, 9)
    os.waitpid(pid, 0)
    raise AssertionError("the forked worker hung")


def test_send_sms_sync_queues_the_same_draft_it_used_to_post():
    missive = MissiveAPI()
    with patch.object(missive.sms_sender, "submit") as submit:
        missive.send_sms_sync("answer", PHONE, conversation_id="conversation-1", add_label_list=["lookup"])

    submit.assert_called_once_with({
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


def test_a_zero_retry_after_still_waits_a_second():
    waits = []
    responses = [missive_response(429, {"error": {"params": {"retry_after": 0}}}), missive_response(201)]
    sender = OrderedSender(lambda body: responses.pop(0), clock=FakeClock(now=0), sleep=waits.append)

    sender.deliver(draft("answer"), queued_at=0)

    assert waits == [1]


def test_network_error_logs_leave_out_the_phone_number_message_and_token(logs):
    def post(body):
        headers = {"Authorization": "Bearer secret-token"}
        raise requests.ConnectionError(f"could not reach Missive with {headers} and {body}")

    OrderedSender(post).deliver(draft("We don't have info for 1111 E. Jefferson"), queued_at=0)

    logged = " ".join(record["message"] for record in logs)
    assert all(record["exception"] is None for record in logs)
    assert PHONE not in logged and "Jefferson" not in logged and "secret-token" not in logged


def test_unexpected_errors_are_logged_without_the_traceback(logs):
    def post(body):
        raise RuntimeError(f"broken while sending {body}")

    sender = OrderedSender(post, sleep=lambda seconds: None)
    sender.submit(draft("answer"))

    for _ in range(50):
        if any(record["level"].name == "ERROR" for record in logs):
            break
        threading.Event().wait(0.1)
    errors = [record for record in logs if record["level"].name == "ERROR"]
    assert [(record["message"], record["exception"]) for record in errors] == [
        ("Missive sender failed to send a lookup SMS: RuntimeError", None)
    ]


def test_replies_still_queued_when_the_worker_exits_are_reported(logs):
    release = threading.Event()
    started = threading.Event()

    def stuck_post(body):
        started.set()
        release.wait(timeout=5)
        return missive_response(201)

    sender = OrderedSender(stuck_post, sleep=lambda seconds: None)
    sender.submit(draft("answer"))
    sender.submit(draft("follow-up"))
    assert started.wait(timeout=5)

    sender.report_unsent()
    release.set()

    assert [record["message"] for record in logs if record["level"].name in ("WARNING", "ERROR")] == [
        "Worker exiting with 2 lookup SMS not yet sent to Missive",
        "Worker exited with lookup SMS still queued for Missive",
    ]


@pytest.fixture
def sentry_events():
    events = []
    sentry_sdk.init(
        dsn="http://public@127.0.0.1:1/1",
        integrations=[LoguruIntegration(level=LoggingLevels.INFO.value, event_level=LoggingLevels.ERROR.value)],
        before_send=lambda event, hint: events.append(event),
    )
    yield events
    sentry_sdk.init()


def test_sentry_events_carry_the_breadcrumbs_of_the_request_that_queued_the_sms(sentry_events):
    sender = OrderedSender(lambda body: missive_response(400), sleep=lambda seconds: None)
    with sentry_sdk.isolation_scope():
        logger.info("first request")
        sender.submit(draft("answer"))
    with sentry_sdk.isolation_scope():
        logger.info("second request")
        sender.submit(draft("answer"))

    for _ in range(50):
        if len(sentry_events) == 2:
            break
        threading.Event().wait(0.1)
    second_request_crumbs = " ".join(crumb["message"] for crumb in sentry_events[1]["breadcrumbs"]["values"])
    assert "second request" in second_request_crumbs and "first request" not in second_request_crumbs


def test_a_worker_that_sent_everything_exits_quietly(logs):
    sent = threading.Event()
    sender = OrderedSender(lambda body: sent.set() or missive_response(201), sleep=lambda seconds: None)
    sender.submit(draft("answer"))
    assert sent.wait(timeout=5)

    for _ in range(50):
        logs.clear()
        sender.report_unsent()
        if not logs:
            break
        threading.Event().wait(0.1)

    assert logs == []
