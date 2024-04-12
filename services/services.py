from configs.database import Session
from models import mi_wayne  # import the model


def search_service(query):
    session = Session()

    results = session.query(mi_wayne).filter(mi_wayne.address.like(f"%{query}%")).all()

    if not results:
        return None

    closest_match = results[0].address
    return closest_match
