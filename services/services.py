import os
import time

from flask import jsonify
from loguru import logger

from configs.database import Session
from configs.query_engine.owner_information_without_sunit import (
    owner_query_engine_without_sunit,
)
from configs.query_engine.tax_information import tax_query_engine
from configs.query_engine.tax_information_without_sunit import tax_query_engine_without_sunit
from libs.MissiveAPI import MissiveAPI
from models import mi_wayne_detroit
from templates.sms import get_rental_message, get_tax_message, sms_templates
from utils.address_normalizer import get_first_valid_normalized_address, extract_latest_address
from utils.check_property_status import check_property_status
from utils.map_keys_to_result import map_keys_to_result

missive_client = MissiveAPI()


def search_service(query, conversation_id, to_phone):
    session = Session()
    results = []
    sunit = ""

    # Run query engine to get address
    normalized_address = get_first_valid_normalized_address([query])
    address, sunit = extract_address_information(normalized_address)

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
                            & (mi_wayne_detroit.sunit.endswith(sunit))
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

    display_address = address if not sunit else address + " " + sunit
    if not results:
        return handle_no_match(display_address, conversation_id, to_phone)
    if len(results) > 1:
        return handle_ambiguous(display_address, conversation_id, to_phone)

    # Missive API to adding tags
    exact_match = results[0].address
    query_result = owner_query_engine_without_sunit.query(exact_match)

    if not "result" in query_result.metadata:
        logger.error(query_result)
    owner_data = map_keys_to_result(query_result.metadata)
    if "owner" in owner_data and "LAND BANK" in owner_data["owner"].upper():
        query_result = sms_templates["land_bank"]

    return handle_match(query_result, conversation_id, to_phone)


def more_search_service(conversation_id, to_phone):
    messages = missive_client.extract_preview_content(conversation_id=conversation_id)
    normalized_address = extract_latest_address(messages, conversation_id, to_phone)
    if not normalized_address:
        logger.error("Couldn't parse address from history messages", messages)
        return (
            jsonify({"message": "Couldn't parse address from history messages"}),
            200,
        )

    address, sunit = extract_address_information(normalized_address)

    if sunit:
        query_result = tax_query_engine.query(str({"address": address, "sunit": sunit}))
    else:
        query_result = tax_query_engine_without_sunit.query(str({"address": {address}}))

    if "result" not in query_result.metadata:
        logger.error(query_result)
    tax_status, rental_status = check_property_status(query_result)

    process_statuses(tax_status, rental_status, conversation_id, to_phone)


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
        )
        time.sleep(2)

    if rental_status:
        missive_client.send_sms_sync(
            get_rental_message(rental_status),
            conversation_id=conversation_id,
            to_phone=phone,
        )
        time.sleep(2)

    missive_client.send_sms_sync(
        sms_templates["final"],
        conversation_id=conversation_id,
        to_phone=phone,
    )


def extract_address_information(normalized_address):
    address = normalized_address.get("address_line_1", "")
    address_line_2 = normalized_address.get("address_line_2")
    if address_line_2 is not None:
        sunit = " ".join(address_line_2.replace("UNIT", "").replace("#", "").split())
    else:
        sunit = ""

    return address, sunit
