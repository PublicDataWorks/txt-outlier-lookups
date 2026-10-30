import atexit
import os
import queue
import threading
import time

import requests
import sentry_sdk
from loguru import logger
from sentry_sdk.scope import use_isolation_scope, use_scope

# Missive allows 900 requests per fixed 15-minute window. On broadcast evenings the broadcast drains
# every window, so a reply may have to wait out one window and then compete for the next.
GIVE_UP_AFTER_SECONDS = 30 * 60
DEFAULT_RETRY_AFTER_SECONDS = 60
GAP_BETWEEN_SENDS_SECONDS = 2


def retry_after_seconds(response):
    try:
        seconds = int(response.json()["error"]["params"]["retry_after"])
    except (ValueError, KeyError, TypeError):
        header = response.headers.get("Retry-After", "")
        seconds = int(header) if header.isdigit() else DEFAULT_RETRY_AFTER_SECONDS
    return max(seconds, 1)


class OrderedSender:
    """Sends Missive drafts one at a time, in the order they were submitted, waiting out 429s.

    Gunicorn forks its workers after main.py is imported, and a thread does not survive a fork,
    so each process starts its own sending thread the first time it submits.

    Failures are logged without exception info on purpose: Sentry and loguru would otherwise
    record the frame locals, which hold the resident's phone number, the SMS and the API token.
    """

    def __init__(self, post, clock=time.monotonic, sleep=time.sleep):
        self._post = post
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._jobs = None
        self._jobs_pid = None
        self._unsent = 0
        self._exit_hook_registered = False

    def submit(self, body):
        # The thread outlives the request, so each job carries the scopes of the request that queued it.
        job = (self._clock(), body, sentry_sdk.get_isolation_scope().fork(), sentry_sdk.get_current_scope().fork())
        with self._lock:
            self._jobs_for_this_process().put(job)
            self._unsent += 1

    def report_unsent(self):
        if self._unsent and self._jobs_pid == os.getpid():
            logger.warning(f"Worker exiting with {self._unsent} lookup SMS not yet sent to Missive")
            logger.error("Worker exited with lookup SMS still queued for Missive")

    def _jobs_for_this_process(self):
        if self._jobs_pid != os.getpid():
            self._jobs = queue.Queue()
            self._jobs_pid = os.getpid()
            self._unsent = 0
            threading.Thread(target=self._run, args=(self._jobs,), name="missive-sender", daemon=True).start()
            if not self._exit_hook_registered:
                atexit.register(self.report_unsent)
                self._exit_hook_registered = True
        return self._jobs

    def _run(self, jobs):
        while True:
            queued_at, body, isolation_scope, current_scope = jobs.get()
            with use_isolation_scope(isolation_scope), use_scope(current_scope):
                try:
                    self.deliver(body, queued_at)
                except Exception as error:
                    logger.error(f"Missive sender failed to send a lookup SMS: {type(error).__name__}")
            with self._lock:
                self._unsent -= 1
            self._sleep(GAP_BETWEEN_SENDS_SECONDS)

    def deliver(self, body, queued_at):
        conversation = body["drafts"].get("conversation")
        response = self._attempt(body)
        while response is not None and response.status_code == 429:
            wait = retry_after_seconds(response)
            if self._clock() + wait - queued_at > GIVE_UP_AFTER_SECONDS:
                logger.warning(f"Missive still rate limited the SMS for conversation {conversation}, dropping it")
                logger.error("Dropped a lookup SMS: Missive kept rate limiting it for 30 minutes")
                return None
            logger.warning(f"Missive rate limited the SMS for conversation {conversation}, retrying in {wait}s")
            self._sleep(wait)
            response = self._attempt(body)

        if response is None:
            return None
        if not response.ok:
            logger.warning(f"Missive rejected the SMS for conversation {conversation}")
            logger.error(f"Missive send message failed with status code {response.status_code}")
            return None
        return response

    def _attempt(self, body):
        try:
            return self._post(body)
        except requests.RequestException as error:
            logger.error(f"Missive send message failed: {type(error).__name__}")
            return None
