import os
import sys
import threading
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from loguru import logger
from sentry_sdk.integrations.loguru import LoggingLevels, LoguruIntegration
from werkzeug.middleware.proxy_fix import ProxyFix
import sentry_sdk

from configs.cache_template import init_lookup_templates_cache, cache
from configs.query_engine.owner_information import init_owner_query_engine
from configs.query_engine.owner_information_without_sunit import (
    init_owner_query_engine_without_sunit
)
from configs.query_engine.tax_information import init_tax_query_engine
from configs.query_engine.tax_information_without_sunit import init_tax_query_engine_without_sunit
from configs.supabase import run_websocket_listener
from cron.property import fetch_data
from exceptions import APIException
from libs.MissiveAPI import MissiveAPI
from services.services import (
    extract_address_information,
    handle_match,
    search_service,
    more_search_service,
)
from utils.address_normalizer import extract_latest_address

load_dotenv(override=True)

sentry_loguru = LoguruIntegration(
    level=LoggingLevels.INFO.value,  # Capture info and above as breadcrumbs
    event_level=LoggingLevels.ERROR.value,  # Send errors as events
)

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DNS"),
    enable_tracing=True,
    integrations=[sentry_loguru],
)

logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")

app = Flask(__name__)

os.makedirs('cache', exist_ok=True)
cache.init_app(app=app, config={"CACHE_TYPE": "FileSystemCache", 'CACHE_DIR': Path('./cache')})

with app.app_context():
    init_lookup_templates_cache()

# owner_query_engine = init_owner_query_engine()
# owner_query_engine_without_sunit = init_owner_query_engine_without_sunit()
# tax_query_engine = init_tax_query_engine()
# tax_query_engine_without_sunit = init_tax_query_engine_without_sunit()


@app.errorhandler(APIException)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

missive_client = MissiveAPI()


@app.route("/", methods=["GET"])
def health_check():
    return "OK"


@app.route("/search", methods=["POST"])
# @require_authentication
def search():
    try:
        data = request.get_json()
        conversation_id = data.get("conversation", {}).get("id")
        to_phone = data.get("message", {}).get("from_field", {}).get("id")
        message = data.get("message", {}).get("preview")
        response, status = search_service(
            query=message, conversation_id=conversation_id, to_phone=to_phone,
            owner_query_engine_without_sunit=owner_query_engine_without_sunit
        )
        return jsonify(response), status

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route("/yes", methods=["POST"])
def yes():
    try:
        data = request.get_json()
        conversation_id = data.get("conversation", {}).get("id")
        to_phone = data.get("message", {}).get("from_field", {}).get("id")
        messages = missive_client.extract_preview_content(conversation_id=conversation_id)
        normalized_address = extract_latest_address(
            messages=messages, conversation_id=conversation_id, to_phone=to_phone
        )
        if not normalized_address:
            logger.error("Couldn't parse address from history messages", messages)
            return (
                jsonify({"message": "Couldn't parse address from history messages"}),
                200,
            )

        address, sunit = extract_address_information(normalized_address)

        if sunit:
            query_result = owner_query_engine.query(str({"address": address, "sunit": sunit}))
        else:
            query_result = owner_query_engine_without_sunit.query(str({"address": {address}}))

        if "result" not in query_result.metadata:
            logger.error(query_result)

        handle_match(
            response=query_result,
            conversation_id=conversation_id,
            to_phone=to_phone,
        )
        return jsonify({"message": "Success"}), 200
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route("/more", methods=["POST"])
def more():
    try:
        data = request.get_json()
        conversation_id = data.get("conversation", {}).get("id")
        to_phone = data.get("message", {}).get("from_field", {}).get("id")
        shared_labels = data.get("conversation", {}).get("shared_labels", [])
        shared_label_ids = [label.get("id") for label in shared_labels]

        if shared_label_ids and os.environ.get("MISSIVE_LOOKUP_TAG_ID") in shared_label_ids:

            more_search_service(
                conversation_id=conversation_id, to_phone=to_phone,
                tax_query_engine=tax_query_engine, tax_query_engine_without_sunit=tax_query_engine_without_sunit
            )

            return jsonify({"message": "Success"}), 200

        else:
            return (
                jsonify({"error": "There was no ADDRESS_LOOKUP_TAG, try again later"}),
                200,
            )

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        logger.exception("", e)
        return jsonify({"error": str(e)}), 500


@app.route("/test", methods=["POST"])
def test():
    fetch_data()


def start_mqtt():
    t = threading.Thread(target=run_websocket_listener)
    t.daemon = True
    t.start()


if __name__ == "__main__":
    start_mqtt()
    app.run(port=8080, host="0.0.0.0")
