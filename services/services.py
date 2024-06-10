import os
import time

from flask import jsonify
from loguru import logger

from configs.cache_template import get_template_content_by_name
from configs.database import Session

from libs.MissiveAPI import MissiveAPI
from models import mi_wayne_detroit
from configs.cache_template import get_rental_message, get_tax_message
from models import data_lookup, mi_wayne_detroit, residential_rental_registrations
from models import lookup_history, mi_wayne_detroit, residential_rental_registrations
from templates.sms import get_rental_message, get_tax_message, sms_templates
from utils.address_normalizer import get_first_valid_normalized_address, extract_latest_address
from utils.check_property_status import check_property_status

from sqlalchemy import and_, case, func, or_

missive_client = MissiveAPI()


def search_service(query, conversation_id, to_phone, owner_query_engine_without_sunit):
    session = Session()
    results = []
    is_landbank = False

    # Run query engine to get address
    normalized_address = get_first_valid_normalized_address([query])
    address, sunit = extract_address_information(normalized_address)
    rental_status_case = case(
        (residential_rental_registrations.lat.isnot(None), "REGISTERED"), else_="UNREGISTERED"
    ).label("rental_status")

    if not address:
        logger.error("Wrong format address", query)
        return handle_wrong_format(conversation_id=conversation_id, to_phone=to_phone)
    else:
        if sunit:
            results = (
                session.query(
                    mi_wayne_detroit.address,
                    rental_status_case,
                    mi_wayne_detroit.tax_status,
                    mi_wayne_detroit.szip5,
                    mi_wayne_detroit.tax_due,
                )
                .outerjoin(
                    residential_rental_registrations,
                    and_(
                        func.ST_DWithin(
                            mi_wayne_detroit.wkb_geometry,
                            residential_rental_registrations.wkb_geometry,
                            0.001,
                        ),
                        func.strict_word_similarity(
                            func.upper(mi_wayne_detroit.saddstr),
                            func.upper(residential_rental_registrations.street_name),
                        )
                        > 0.8,
                        mi_wayne_detroit.saddno == residential_rental_registrations.street_num,
                    ),
                )
                .filter(
                    mi_wayne_detroit.address.ilike(f"{address.strip()}%"),
                    or_(
                        mi_wayne_detroit.sunit.ilike(f"%{sunit}%"),
                    ),
                )
                .all()
            )
        else:
            results = (
                session.query(
                    mi_wayne_detroit.address,
                    rental_status_case,
                    mi_wayne_detroit.tax_status,
                    mi_wayne_detroit.szip5,
                    mi_wayne_detroit.tax_due,
                )
                .outerjoin(
                    residential_rental_registrations,
                    and_(
                        func.ST_DWithin(
                            mi_wayne_detroit.wkb_geometry,
                            residential_rental_registrations.wkb_geometry,
                            0.001,
                        ),
                        func.strict_word_similarity(
                            func.upper(mi_wayne_detroit.saddstr),
                            func.upper(residential_rental_registrations.street_name),
                        )
                        > 0.8,
                        mi_wayne_detroit.saddno == residential_rental_registrations.street_num,
                    ),
                )
                .filter(
                    mi_wayne_detroit.address.ilike(f"{address.strip()}%"),
                )
                .all()
            )

    display_address = address if not sunit else address + " " + sunit
    if not results:
        return handle_no_match(display_address, conversation_id, to_phone)

    address, rental_status, tax_status, zip_code, tax_due = results[0]

    if not tax_status and tax_due and int(tax_due) > 0:
        add_data_lookup_to_db(
            address,
            zip_code,
            "TAX_DEBT",
            rental_status,
        )
    else:
        add_data_lookup_to_db(
            address,
            zip_code,
            "NO_TAX_DEBT",
            rental_status,
        )


    if len(results) > 1:
        return handle_ambiguous(display_address, conversation_id, to_phone)

    # Missive API to adding tags
    query_result = owner_query_engine_without_sunit.query(address)

    if "result" not in query_result.metadata:
        logger.error(query_result)
        return "", 200

    owner_data = map_keys_to_result(query_result.metadata)

    if "owner" in owner_data:
        if "LAND BANK" in owner_data["owner"].upper():
            is_landbank = True
        elif "UNCONFIRMED" in owner_data["tax_status"].upper():
            query_result = get_template_content_by_name("tax_unconfirmed")

    return handle_match(query_result, conversation_id, to_phone, is_landbank, rental_status)


def more_search_service(conversation_id, to_phone, tax_query_engine, tax_query_engine_without_sunit):
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
        return "", 200

    tax_status, rental_status = check_property_status(query_result)
    process_statuses(tax_status, rental_status, conversation_id, to_phone)


def handle_no_match(query, conversation_id, to_phone):
    # Missive API -> Send SMS template
    content = get_template_content_by_name("no_match")
    if content:
        formatted_content = content.format(address=query)
        missive_client.send_sms_sync(
            formatted_content,
            to_phone,
            conversation_id,
        )
        return {"result": formatted_content}, 200
    else:
        logger.exception("Could not find template no_match")
        return {"result": ""}, 200


def handle_ambiguous(query, conversation_id, to_phone):
    # Missive API -> Send SMS template
    content = get_template_content_by_name("closest_match")
    if content:
        formatted_content = content.format(address=query)
        missive_client.send_sms_sync(
            formatted_content,
            to_phone,
            conversation_id,
        )
        return {"result": formatted_content}, 200
    else:
        logger.exception("Could not find template closest_match")
        return {"result": ""}, 200


def handle_match(
        response,
        conversation_id,
        to_phone,
        is_landbank=False,
        rental_status=False
):
    response = str(response)
    if rental_status == "REGISTERED":
        response += "It is registered as a residential rental property"

    # Missive API -> Send SMS template
    missive_client.send_sms_sync(
        str(response),
        conversation_id=conversation_id,
        to_phone=to_phone,
        add_label_list=[os.environ.get("MISSIVE_LOOKUP_TAG_ID")],
    )

    time.sleep(2)

    content = ""
    if is_landbank:
        content = get_template_content_by_name("land_bank")
    else:
        content = get_template_content_by_name("match_second_message")

    if content:
        formatted_content = content.format(response=response)
        missive_client.send_sms_sync(
            formatted_content,
            conversation_id=conversation_id,
            to_phone=to_phone,
            add_label_list=[os.environ.get("MISSIVE_LOOKUP_TAG_ID")],
        )
    # Remove tags
    return {"result": str(response)}, 200


def handle_wrong_format(conversation_id, to_phone):
    content = get_template_content_by_name("wrong_format")
    if content:
        missive_client.send_sms_sync(
            content,
            conversation_id=conversation_id,
            to_phone=to_phone,
        )
        return {"result": content}, 200
    else:
        logger.exception("Could not find template wrong_format")
        return {"result": ""}, 200


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

    content = get_template_content_by_name("final")
    if content:
        missive_client.send_sms_sync(
            content,
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


def add_data_lookup_to_db(address, zip_code, tax_status, rental_status):
    session = Session()
    try:
        new_data_lookup = lookup_history(
            address=address, zip_code=zip_code, tax_status=tax_status, rental_status=rental_status
        )
        session.add(new_data_lookup)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_address_information(session, address):
    normalized_address = get_first_valid_normalized_address([address])
    address, sunit = extract_address_information(normalized_address)

    # Define the case statement for rental_status
    rental_status_case = case(
        (residential_rental_registrations.lat.isnot(None), "IS"), else_="IS NOT"
    ).label("rental_status")

    query = (
        session.query(
            rental_status_case,
            mi_wayne_detroit.tax_due,
            mi_wayne_detroit.tax_status,
            mi_wayne_detroit.szip5,
        )
        .outerjoin(
            residential_rental_registrations,
            and_(
                func.ST_DWithin(
                    mi_wayne_detroit.wkb_geometry,
                    residential_rental_registrations.wkb_geometry,
                    0.001,
                ),
                func.strict_word_similarity(
                    mi_wayne_detroit.address,
                    residential_rental_registrations.street_num
                    + " "
                    + residential_rental_registrations.street_name,
                )
                > 0.8,
            ),
        )
        .filter(
            mi_wayne_detroit.address.ilike(f"{address.strip()}%"),
            or_(
                mi_wayne_detroit.sunit.ilike(f"%{sunit}%"),
                mi_wayne_detroit.sunit == "",
                mi_wayne_detroit.sunit.is_(None),
            ),
        )
    )

    results = query.all()
    return results
