from loguru import logger

from configs.database import Session
from models import LookupTemplate
from templates.templates import templates
from flask_caching import Cache

session = Session()
cache = Cache()


def get_lookup_templates():
    lookup_templates = session.query(LookupTemplate).all()
    return [template.__dict__ for template in lookup_templates]


def init_lookup_templates_cache():
    lookup_templates = get_lookup_templates()
    lookup_templates_dict = {template['name']: template['content'] for template in lookup_templates}
    cache.set("lookup_templates", lookup_templates_dict)


def get_template_content_by_name(name):
    if cache:
        lookup_templates_dict = cache.get("lookup_templates")
        if lookup_templates_dict:
            template = lookup_templates_dict.get(name)
            if template:
                return template
    # Fallback to sms_templates if the key is not found in the cache
    fallback_template = templates.get(name)
    if fallback_template:
        return fallback_template
    logger.error("Could not get template")
    return None


def update_lookup_templates_cache():
    lookup_templates = get_lookup_templates()
    lookup_templates_dict = {template['name']: template['content'] for template in lookup_templates}
    cache.set("lookup_templates", lookup_templates_dict)


def get_tax_message(tax_status):
    tax_status_mapping = {
        "TAX_DEBT": get_template_content_by_name("has_tax_debt"),
        "FORECLOSED": get_template_content_by_name("foreclosed"),
        "FORFEITED": get_template_content_by_name("forfeited"),
        "NO_INFORMATION": None,
    }

    return tax_status_mapping.get(tax_status, "Invalid tax status")


def get_rental_message(rental_status):
    rental_status_mapping = {
        "REGISTERED": get_template_content_by_name("registered"),
        "UNREGISTERED": get_template_content_by_name("unregistered"),
        "NO_INFORMATION": None,
    }

    return rental_status_mapping.get(rental_status, "Invalid rental status")
