from apscheduler.schedulers.background import BackgroundScheduler
from flask_caching import Cache

from configs.database import Session
from models import LookupTemplate

cache = Cache()
session = Session()


def get_lookup_templates():
    lookup_templates = session.query(LookupTemplate).all()
    return [template.__dict__ for template in lookup_templates]


def init_lookup_templates_cache():
    lookup_templates = get_lookup_templates()
    lookup_templates_dict = {template['name']: template['content'] for template in lookup_templates}
    cache.set("lookup_templates", lookup_templates_dict)


def get_template_content_by_name(name):
    lookup_templates_dict = cache.get("lookup_templates")
    if lookup_templates_dict:
        return lookup_templates_dict.get(name)
    return None


def update_lookup_templates_cache():
    lookup_templates = get_lookup_templates()
    lookup_templates_dict = {template['name']: template['content'] for template in lookup_templates}
    cache.set("lookup_templates", lookup_templates_dict)


