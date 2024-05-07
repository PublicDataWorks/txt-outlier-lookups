import os


from loguru import logger
from configs.database import Session
from configs.query_engine.owner_information_without_sunit import owner_query_engine_without_sunit
from configs.query_engine.owner_information import owner_query_engine
from libs.MissiveAPI import MissiveAPI
from models import mi_wayne_detroit
from templates.sms import get_rental_message, get_tax_message, sms_templates
from utils.address_normalizer import (
    get_first_valid_normalized_address,
)
from sqlalchemy import or_
import time


missive_client = MissiveAPI()


def search_service(query, conversation_id, to_phone):
    session = Session()
    results = []

    # Run query engine to get address
    normalize_address = get_first_valid_normalized_address([query])
    address = normalize_address.get("address_line_1", "")
    sunit = " ".join(normalize_address.get("address_line_2", "").replace("UNIT", "").split())
    query_result = []

    if not address:
        logger.error("Wrong format address", query)
        return handle_wrong_format(conversation_id=conversation_id, to_phone=to_phone)
    else:
        if sunit:
            results = (
                session.query(mi_wayne_detroit)
                .filter(
                    (
                        mi_wayne_detroit.address.ilike(f"{address.strip()}%")
                        & (
                            (mi_wayne_detroit.sunit == sunit)
                            | (mi_wayne_detroit.sunit_suffix == sunit)
                        )
                    )
                )
                .all()
            )
        else:
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
    query_result = owner_query_engine_without_sunit.query(exact_match)

    if not "result" in query_result.metadata:
        logger.error(query_result)
    return handle_match(query_result, conversation_id, to_phone)


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
    missive_client.send_sms_sync(
        str(response),
        conversation_id=conversation_id,
        to_phone=to_phone,
        add_label_list=[os.environ.get("MISSIVE_LOOKUP_TAG_ID")],
    )

    time.sleep(2)

    missive_client.send_sms_sync(
        sms_templates["match_second_message"],
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
    if tax_status and tax_status != "NO_TAX_DEBT":
        missive_client.send_sms_sync(
            get_tax_message(tax_status),
            conversation_id=conversation_id,
            to_phone=phone,
            remove_label_list=[os.environ.get("MISSIVE_LOOKUP_TAG_ID")],
        )
        time.sleep(2)

    if rental_status:
        missive_client.send_sms_sync(
            get_rental_message(rental_status),
            conversation_id=conversation_id,
            to_phone=phone,
            remove_label_list=[os.environ.get("MISSIVE_LOOKUP_TAG_ID")],
        )
        time.sleep(2)

    missive_client.send_sms_sync(
        sms_templates["final"],
        conversation_id=conversation_id,
        to_phone=phone,
        remove_label_list=[os.environ.get("MISSIVE_LOOKUP_TAG_ID")],
    )
