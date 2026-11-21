"""Retries for the steps of an address lookup that only read: the address parser, the property query and the
owner summary. A lookup that fails once and then works should send the resident the normal reply; only a lookup
that keeps failing should reach /search's catch-all, which texts the resident that we had an error (OUT-423).

Nothing that sends an SMS is retried here: a retry must never text a resident twice.
"""
from time import monotonic, sleep

import sentry_sdk
from loguru import logger

# Tries per step when it raises, counting the first.
ATTEMPTS = 3
# Seconds to wait before the second and the third try.
BACKOFF_SECONDS = (1, 3)
# Tries of the owner summary when it comes back empty, counting the first.
EMPTY_ATTEMPTS = 2
# A retry only starts while the lookup has run for less than this. The OpenAI client already retries a slow call
# itself (up to 60 s each), so without a budget a hung model could keep the resident waiting for minutes.
RETRY_BUDGET_SECONDS = 45

EMPTY = "empty answer"
RECOVERED = "recovered"
GAVE_UP = "gave_up"


class LookupRetries:
    """One per lookup, so every step shares the lookup's time budget."""

    def __init__(self, conversation_id, clock=monotonic):
        self.conversation_id = conversation_id
        self.clock = clock
        self.started = clock()

    def run(self, step, call, is_empty=None):
        """Returns call()'s result, trying again when it raises or, given is_empty, when the result is empty.
        Once the tries or the time run out it raises the last error, or returns the last empty result."""
        problems = []
        while True:
            try:
                result = call()
            except Exception as error:
                problems.append(type(error).__name__)
                failure, limit = error, ATTEMPTS
            else:
                if is_empty is None or not is_empty(result):
                    if problems:
                        self._outcome(step, RECOVERED, problems)
                    return result
                problems.append(EMPTY)
                failure, limit = None, EMPTY_ATTEMPTS

            attempt = len(problems)
            if attempt >= limit or not self._time_left():
                self._outcome(step, GAVE_UP, problems)
                if failure is not None:
                    raise failure
                return result
            wait = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS)) - 1]
            logger.info(f"[lookup_retry] {step} try {attempt} failed ({problems[-1]}) for conversation "
                        f"{self.conversation_id}, trying again in {wait}s")
            sleep(wait)

    def _time_left(self):
        return self.clock() - self.started < RETRY_BUDGET_SECONDS

    def _outcome(self, step, outcome, problems):
        """One log line and one Sentry event per step that failed at least once, so we can count how often a
        retry rescues a lookup. Error names and the step only: never the resident's text, number or address."""
        tries = len(problems) + (outcome == RECOVERED)
        if outcome == RECOVERED:
            logger.info(f"[lookup_retry] {step} recovered on try {tries} for conversation {self.conversation_id} "
                        f"(failures: {', '.join(problems)})")
        else:
            logger.warning(f"[lookup_retry] {step} gave up after {tries} tries for conversation "
                           f"{self.conversation_id} (failures: {', '.join(problems)})")
        try:
            sentry_sdk.capture_message(
                f"Lookup {step} {'recovered on a retry' if outcome == RECOVERED else 'failed every retry'}",
                level="info" if outcome == RECOVERED else "warning",
                fingerprint=["lookup-retry", step, outcome],
                tags={
                    "step": step,
                    "outcome": outcome,
                    "tries": str(tries),
                    "first_failure": problems[0],
                    "conversation_id": self.conversation_id,
                },
            )
        except Exception as error:
            logger.error(f"Reporting a lookup retry to Sentry failed: {type(error).__name__}")
