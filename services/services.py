from flask import g

from configs.database import Session
from configs.query_engine.owner import owner_query_engine
from libs.MissiveAPI import MissiveAPI
from models import mi_wayne  # import the model
from templates.sms import sms_templates

missive_client = MissiveAPI()


def search_service(query, conversation_id, to_phone):
    session = Session()
    results = session.query(mi_wayne).filter(mi_wayne.address.like(f"{query}%")).all()

    if not results:
        return handle_no_match(conversation_id, to_phone)

    if len(results) > 1:
        return handle_ambiguous(conversation_id, to_phone)

    # Missive API to adding tags
    exact_match = results[0].address
    return handle_match(exact_match, conversation_id, to_phone)


def handle_no_match(conversation_id, to_phone):
    # Missive API -> Send SMS template
    missive_client.send_sms(
        sms_templates["no_match"],
        to_phone,
        conversation_id,
    )
    return {"result": sms_templates["no_match"]}, 200


def handle_ambiguous(conversation_id, to_phone):
    # Missive API -> Send SMS template
    missive_client.send_sms(
        sms_templates["closest_match"],
        to_phone,
        conversation_id,
    )
    return {"result": sms_templates["closest_match"]}, 200


def handle_match(
    match_data,
    conversation_id,
    to_phone,
):
    # Missive API -> Send SMS template
    response = owner_query_engine.query(match_data)
    missive_client.send_sms(
        response,
        to_phone,
        conversation_id,
    )
    # Remove tags
    return {"result": str(response)}, 200
