import hashlib
import os
import random
import time

from loguru import logger

# Missive retries a webhook that gets no answer within 15 seconds, up to 5 times over 8 minutes, and a
# lookup's LLM calls can take longer than that. A claim outlives the last retry.
CLAIM_SECONDS = 15 * 60
# One file per claim, in a directory of its own: the flask-caching file cache prunes entries once it has
# too many, and claims there could push out the lookup templates.
CLAIMS_DIR = os.path.join("cache", "webhook-claims")
SWEEP_ONE_IN = 100


def claim_webhook(message_id, directory=CLAIMS_DIR, clock=time.time):
    """True the first time a webhook's message id is seen in this container, across gunicorn workers.
    Answers True when there is no id, or when the claim can't be checked, so the lookup still runs."""
    if not message_id:
        return True
    try:
        os.makedirs(directory, exist_ok=True)
        # Hashed, so the id can't choose where the file goes.
        path = os.path.join(directory, hashlib.sha256(str(message_id).encode()).hexdigest())
        claimed = _create(path) or (_expired(path, clock) and _remove(path) and _create(path))
        if claimed and random.randrange(SWEEP_ONE_IN) == 0:
            sweep_expired_claims(directory, clock)
        return claimed
    except OSError as error:
        logger.error(f"Checking for a repeated webhook failed: {type(error).__name__}")
        return True


def _create(path):
    # O_EXCL makes the check and the create one step, so two workers can't both claim the same id.
    try:
        os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
    except FileExistsError:
        return False
    return True


def _expired(path, clock):
    try:
        return clock() - os.path.getmtime(path) > CLAIM_SECONDS
    except FileNotFoundError:
        return True


def _remove(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    return True


def sweep_expired_claims(directory=CLAIMS_DIR, clock=time.time):
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return
    for entry in entries:
        try:
            if clock() - entry.stat().st_mtime > CLAIM_SECONDS:
                os.remove(entry.path)
        except OSError:
            pass
