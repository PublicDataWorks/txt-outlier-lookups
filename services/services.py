import asyncio
import os

from dotenv import load_dotenv
from flask import g

from configs.database import Session
from configs.query_engine.owner import owner_query_engine
from libs.MissiveAPI import MissiveAPI
from models import mi_wayne_detroit
from templates.sms import get_rental_message, get_tax_message, sms_templates

load_dotenv()

missive_client = MissiveAPI()


def search_service(query, conversation_id, to_phone):
    session = Session()
    results = (
        session.query(mi_wayne_detroit)
        .filter(mi_wayne_detroit.address.ilike(f"{query.strip()}%"))
        .all()
    )

    if not results:
        return asyncio.run(handle_no_match(query, conversation_id, to_phone))
    if len(results) > 1:
        return asyncio.run(handle_ambiguous(query, conversation_id, to_phone))

    # Missive API to adding tags
    exact_match = results[0].address
    response = owner_query_engine.query(exact_match)
    return asyncio.run(handle_match(response, conversation_id, to_phone))


async def handle_no_match(query, conversation_id, to_phone):
    # Missive API -> Send SMS template
    await missive_client.send_sms(
        sms_templates["no_match"].format(address=query),
        to_phone,
        conversation_id,
    )
    return {"result": sms_templates["no_match"]}, 200


async def handle_ambiguous(query, conversation_id, to_phone):
    # Missive API -> Send SMS template
    await missive_client.send_sms(
        sms_templates["closest_match"].format(address=query),
        to_phone,
        conversation_id,
    )
    return {"result": sms_templates["closest_match"]}, 200


async def handle_match(
    response,
    conversation_id,
    to_phone,
):
    # Missive API -> Send SMS template
    await missive_client.send_sms(
        response,
        to_phone,
        conversation_id,
        add_label_list=[os.environ.get("MISSIVE_LOOKUP_TAG_ID")],
    )

    if response.metadata:
        await missive_client.send_sms(
            sms_templates["match_second_message"],
            to_phone,
            conversation_id,
        )

    # Remove tags
    return {"result": str(response)}, 200


async def process_statuses(tax_status, rental_status, conversation_id, phone):
    if tax_status:
        await missive_client.send_sms(
            get_tax_message(tax_status),
            conversation_id=conversation_id,
            to_phone=phone,
        )

    if rental_status:
        await missive_client.send_sms(
            get_rental_message(rental_status),
            conversation_id=conversation_id,
            to_phone=phone,
        )

    await missive_client.send_sms(
        sms_templates["final"],
        conversation_id=conversation_id,
        to_phone=phone,
        remove_label_list=[os.environ.get("MISSIVE_LOOKUP_TAG_ID")],
    )


async def warning_not_in_session(conversation_id, to_phone):
    await missive_client.send_sms(
        "You are not currently in a lookup session, please initiate one before querying for more infomation.",
        conversation_id=conversation_id,
        to_phone=to_phone,
    )
