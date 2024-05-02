import os

from dotenv import load_dotenv

from configs.database import Session
from configs.query_engine.owner import owner_query_engine
from libs.MissiveAPI import MissiveAPI
from models import mi_wayne_detroit
from templates.sms import get_rental_message, get_tax_message, sms_templates
from utils.address_normalizer import (
    check_address_format,
    get_first_valid_normalized_address,
)

load_dotenv()

missive_client = MissiveAPI()


def search_service(query, conversation_id, to_phone):
    session = Session()
    address = check_address_format(query)

    if not address:
        # Run query engine to get address
        address = get_first_valid_normalized_address([query])
        if not address:
            return handle_wrong_format(
                conversation_id=conversation_id, to_phone=to_phone
            )

    results = (
        session.query(mi_wayne_detroit)
        .filter(mi_wayne_detroit.address.ilike(f"{address.strip()}%"))
        .all()
    )

    if not results:
        return handle_no_match(query, conversation_id, to_phone)
    if len(results) > 1:
        return handle_ambiguous(query, conversation_id, to_phone)

    # Missive API to adding tags
    exact_match = results[0].address
    response = owner_query_engine.query(exact_match)
    return handle_match(response, conversation_id, to_phone)


def handle_no_match(query, conversation_id, to_phone):
    # Missive API -> Send SMS template
    missive_client.send_sms_sync(
        sms_templates["no_match"].format(address=query),
        to_phone,
        conversation_id,
    )
    return {"result": sms_templates["no_match"]}, 200


def handle_ambiguous(query, conversation_id, to_phone):
    # Missive API -> Send SMS template
    missive_client.send_sms_sync(
        sms_templates["closest_match"].format(address=query),
        to_phone,
        conversation_id,
    )
    return {"result": sms_templates["closest_match"]}, 200


def handle_match(
    response,
    conversation_id,
    to_phone,
):
    # Missive API -> Send SMS template
    messages = [str(response)]
    if response.metadata:
        messages.append(sms_templates["match_second_message"])

    missive_client.send_sms_sync(
        "\n\n".join(messages),
        conversation_id=conversation_id,
        to_phone=to_phone,
        add_label_list=[os.environ.get("MISSIVE_LOOKUP_TAG_ID")],
    )
    # Remove tags
    return {"result": str(response)}, 200


def handle_wrong_format(conversation_id, to_phone):
    missive_client.send_sms_sync(
        sms_templates["wrong_format"],
        conversation_id=conversation_id,
        to_phone=to_phone,
    )
    return {"result": sms_templates["wrong_format"]}, 200


def process_statuses(tax_status, rental_status, conversation_id, phone):
    message = []
    if tax_status:
        message.append(
            get_tax_message(tax_status),
        )

    if rental_status:
        message.append(
            get_rental_message(rental_status),
        )

    message.append(sms_templates["final"])

    missive_client.send_sms_sync(
        "\n\n".join(message),
        conversation_id=conversation_id,
        to_phone=phone,
        remove_label_list=[os.environ.get("MISSIVE_LOOKUP_TAG_ID")],
    )


def warning_not_in_session(conversation_id, to_phone):
    missive_client.send_sms_sync(
        "You are not currently in a lookup session, please initiate one before querying for more infomation.",
        conversation_id=conversation_id,
        to_phone=to_phone,
    )
