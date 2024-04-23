from configs.database import Session
from configs.query_config import query_engine
from models import mi_wayne  # import the model
from templates.sms import sms_templates


def search_service(query):
    session = Session()
    results = session.query(mi_wayne).filter(mi_wayne.address.like(f"{query}%")).all()

    if not results:
        return handle_no_match()

    if len(results) > 1:
        return handle_ambiguous()

    exact_match = results[0].address
    return handle_match(exact_match)


def handle_no_match():
    return {"result": sms_templates["no_match"]}, 200


def handle_ambiguous():
    return {"result": sms_templates["closest_match"]}, 200


def handle_match(match_data):
    response = query_engine.query(match_data)
    return {"result": str(response)}, 200
