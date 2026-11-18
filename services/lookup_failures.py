import os
from contextvars import ContextVar

from loguru import logger

from configs.cache_template import get_template_content_by_name
from libs.MissiveAPI import MissiveAPI
from libs.missive_sender import ANSWER, FALLBACK

missive_client = MissiveAPI()

# Set once a failure is reported, so /search's catch-all doesn't report the same lookup a second time.
# /search resets it for each request: gunicorn's sync workers reuse one thread for every request.
reported = ContextVar("lookup_failure_reported", default=False)

# Why a lookup couldn't reply. These are the only words of the post that change, so they must stay
# fixed text from this module: never the resident's message, number or parsed address.
PARSE_FAILURE = "couldn't read an address in the text"
SYSTEM_ERROR = "system error"
EMPTY_ANSWER = "the owner lookup came back empty"
MISSING_TEMPLATE = "the reply template is missing"
REPLY_DROPPED = "Missive didn't send the reply (rate limited or rejected)"

# Resident-facing code fallback; a lookup_template row named lookup_error overrides it without a deploy.
LOOKUP_ERROR_TEMPLATE = "lookup_error"


def report_lookup_failure(conversation_id, to_phone, kind, notify_resident, detail=None):
    """Leaves a staff note (and the "address lookup failed" label) in the Missive conversation, and,
    when the failure is ours rather than the resident's, texts the resident that a reporter will follow
    up. Never raises: it runs on paths that are already failing."""
    reported.set(True)
    reason = f"{kind} ({detail})" if detail else kind
    if not conversation_id:
        logger.error(f"Couldn't report a lookup that didn't reply, the webhook had no conversation: {reason}")
        return

    texted = notify_resident and _text_resident(conversation_id, to_phone)
    follow_up = (
        "A text telling the resident a reporter will follow up is on its way. If Missive drops it, another note "
        "will say so." if texted else "The resident wasn't texted."
    )
    markdown = f"Automatic address lookup didn't reply: {reason}. {follow_up} Please follow up by hand."

    label_id = os.environ.get("MISSIVE_LOOKUP_FAILED_TAG_ID")
    if not label_id:
        logger.info("MISSIVE_LOOKUP_FAILED_TAG_ID is not set, so the lookup failure post adds no label")
    try:
        missive_client.queue_post(
            [markdown],
            conversation_id,
            notification_title="Address lookup failed",
            add_label_list=[label_id] if label_id else None,
        )
    except Exception as error:
        logger.error(f"Posting a lookup failure to Missive failed: {type(error).__name__}")
        return
    logger.info(f"Reported a lookup that didn't reply for conversation {conversation_id}: {reason}")


def _text_resident(conversation_id, to_phone):
    if not to_phone:
        logger.error(f"Couldn't text the resident about a failed lookup in conversation {conversation_id}: no number")
        return False
    try:
        content = get_template_content_by_name(LOOKUP_ERROR_TEMPLATE)
        if not content:
            return False
        missive_client.send_sms_sync(content, to_phone, conversation_id, role=FALLBACK)
    except Exception as error:
        logger.error(f"Texting the resident about a failed lookup failed: {type(error).__name__}")
        return False
    return True


FALLBACK_DROPPED = "The text telling the resident a reporter will follow up didn't go out. Please reply by hand."


def report_dropped_reply(conversation_id, role=ANSWER):
    """Called by the SMS queue for each SMS Missive never took."""
    if role == FALLBACK:
        # The lookup was already reported; this only corrects that report's "on its way". No label: the
        # first report added it.
        try:
            missive_client.queue_post([FALLBACK_DROPPED], conversation_id, notification_title="Address lookup failed")
        except Exception as error:
            logger.error(f"Posting a dropped lookup error text to Missive failed: {type(error).__name__}")
        return
    if role != ANSWER:
        # A follow-up: the resident already has their answer, so staff have nothing to pick up.
        logger.info(f"A follow-up SMS was dropped after its answer went out, conversation {conversation_id}")
        return
    # Staff only: the queue that would carry a resident text is the one that just failed.
    report_lookup_failure(conversation_id, None, REPLY_DROPPED, notify_resident=False)
