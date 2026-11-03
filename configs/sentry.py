import os

import sentry_sdk
from sentry_sdk.integrations.loguru import LoggingLevels, LoguruIntegration


def message_only(record):
    # A format string would get loguru's traceback appended, annotated with local variables such as the
    # resident's phone number. A format function gets nothing appended; Sentry still reads the exception
    # from the record. Leaving out the default timestamp also lets repeats of an error group as one issue.
    return "{message}"


def drop_request_details(event, hint):
    # The sidebar puts the resident's phone number in the URL: /contacts/<phone> and ?reference=<phone>.
    if "request" in event:
        event["request"] = {"method": event["request"].get("method")}
    return event


def init_sentry(**options):
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DNS"),
        enable_tracing=True,
        integrations=[
            LoguruIntegration(
                level=LoggingLevels.INFO.value,  # Capture info and above as breadcrumbs
                event_level=LoggingLevels.ERROR.value,  # Send errors as events
                breadcrumb_format=message_only,
                event_format=message_only,
            )
        ],
        # Webhook bodies and frame locals hold residents' texts and phone numbers.
        max_request_body_size="never",
        include_local_variables=False,
        before_send=drop_request_details,
        before_send_transaction=drop_request_details,
        **options,
    )
