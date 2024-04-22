from configs.database import Session
from models import mi_wayne  # import the model
from templates.sms import sms_templates


def search_service(query):
    session = Session()
    results = session.query(mi_wayne).filter(mi_wayne.address.like(f"{query}%")).all()

    if not results:
        return sms_templates["no_match"], "NO_MATCH"

    if len(results) > 1:
        return sms_templates["closest_match"], "AMBIGUOUS"

    closest_match = results[0].address
    return closest_match, "MATCH"
