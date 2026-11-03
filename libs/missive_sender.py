import atexit
import os
import queue
import threading
import time

import sentry_sdk
from loguru import logger
from sentry_sdk.scope import use_isolation_scope, use_scope

# Missive allows 900 requests per fixed 15-minute window. On broadcast evenings the broadcast drains
# every window, so a reply may have to wait out one window and then compete for the next.
GIVE_UP_AFTER_SECONDS = 30 * 60
DEFAULT_RETRY_AFTER_SECONDS = 60
# The answer and its follow-up must reach the phone in order, and back-to-back sends can arrive swapped.
GAP_BETWEEN_SENDS_SECONDS = 2
# A worker's exit must fit inside gunicorn's 30 s graceful timeout, after its last request finishes.
EXIT_DRAIN_SECONDS = 5
# One lookup queues all its SMS within about 8 s; the quickest resident retry seen was 84 s later.
SAME_LOOKUP_SECONDS = 30


def retry_after_seconds(response):
    try:
        seconds = int(response.json()["error"]["params"]["retry_after"])
    except (ValueError, KeyError, TypeError, OverflowError):
        header = response.headers.get("Retry-After", "")
        seconds = int(header) if header.isdigit() else DEFAULT_RETRY_AFTER_SECONDS
    return max(seconds, 1)


class OrderedSender:
    """Sends Missive drafts one at a time, in the order they were submitted, waiting out 429s.

    Gunicorn forks its workers after main.py is imported, and a thread does not survive a fork,
    so each process starts its own queue and sending thread the first time it submits.

    Each failure logs a WARNING with the details and an ERROR with fixed text, so Sentry groups one
    issue per kind of failure. Nothing is logged with exception info: Sentry and loguru would record
    the frame locals, which hold the resident's phone number, the SMS and the API token.
    """

    def __init__(self, post, clock=time.monotonic, sleep=time.sleep):
        self._post = post
        self._clock = clock
        self._sleep = sleep
        self._pid = None
        self._start_lock = threading.Lock()
        self._last_post_at = float("-inf")
        self._failed_at = {}
        self._exit_hook_registered = False

    def submit(self, body):
        # Handlers wrapped in async_long_running submit from their own threads, so two may race to start.
        with self._start_lock:
            if self._pid != os.getpid():
                self._start_for_this_process()
        # The thread outlives the request, so each job carries the scopes of the request that queued it.
        job = (self._clock(), body, sentry_sdk.get_isolation_scope().fork(), sentry_sdk.get_current_scope().fork())
        with self._lock:
            self._unsent += 1
        self._jobs.put(job)

    def drain_then_report_unsent(self, timeout=EXIT_DRAIN_SECONDS):
        if self._pid != os.getpid():
            return
        deadline = time.monotonic() + timeout
        while self._unsent and time.monotonic() < deadline:
            time.sleep(0.1)
        if self._unsent:
            logger.warning(f"Worker exiting with {self._unsent} lookup SMS not yet sent to Missive")
            logger.error("Worker exited with lookup SMS still queued for Missive")

    def _start_for_this_process(self):
        self._pid = os.getpid()
        self._lock = threading.Lock()
        self._jobs = queue.Queue()
        self._unsent = 0
        threading.Thread(target=self._run, args=(self._jobs,), name="missive-sender", daemon=True).start()
        # Registered here, not in __init__: the sender is built before main.py sets up Sentry, and atexit runs
        # hooks in reverse order, so an earlier hook would run after Sentry has shut down and lose the report.
        if not self._exit_hook_registered:
            atexit.register(self.drain_then_report_unsent)
            self._exit_hook_registered = True

    def _run(self, jobs):
        while True:
            queued_at, body, isolation_scope, current_scope = jobs.get()
            with use_isolation_scope(isolation_scope), use_scope(current_scope):
                try:
                    self.deliver(body, queued_at)
                except Exception as error:
                    self._failed(body["drafts"].get("conversation"), queued_at)
                    logger.error(f"Missive sender failed to send a lookup SMS: {type(error).__name__}")
            with self._lock:
                self._unsent -= 1

    def deliver(self, body, queued_at):
        conversation = body["drafts"].get("conversation")
        # A follow-up that arrives without its answer only confuses the resident.
        if queued_at - self._failed_at.get(conversation, float("-inf")) <= SAME_LOOKUP_SECONDS:
            logger.warning(f"Skipping the SMS for conversation {conversation}: an earlier SMS of this lookup failed")
            return
        if self._clock() - queued_at > GIVE_UP_AFTER_SECONDS:
            self._drop(conversation, queued_at, "waited over 30 minutes behind rate limited SMS")
            return

        response = self._post_after_gap(body)
        while response.status_code == 429:
            wait = retry_after_seconds(response)
            if self._clock() + wait - queued_at > GIVE_UP_AFTER_SECONDS:
                self._drop(conversation, queued_at, "still rate limited 30 minutes after it was queued")
                return
            logger.warning(f"Missive rate limited the SMS for conversation {conversation}, retrying in {wait}s")
            self._sleep(wait)
            response = self._post_after_gap(body)

        if not response.ok:
            self._failed(conversation, queued_at)
            logger.warning(f"Missive rejected the SMS for conversation {conversation}")
            logger.error(f"Missive send message failed with status code {response.status_code}")

    def _post_after_gap(self, body):
        wait = self._last_post_at + GAP_BETWEEN_SENDS_SECONDS - self._clock()
        if wait > 0:
            self._sleep(wait)
        self._last_post_at = self._clock()
        return self._post(body)

    def _failed(self, conversation, queued_at):
        if conversation is not None:
            self._failed_at[conversation] = queued_at

    def _drop(self, conversation, queued_at, reason):
        self._failed(conversation, queued_at)
        logger.warning(f"Dropping the SMS for conversation {conversation}: {reason}")
        logger.error("Dropped a lookup SMS held up by Missive rate limits")
