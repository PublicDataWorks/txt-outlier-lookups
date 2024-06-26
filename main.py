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
from configs.query_engine.owner_information_without_sunit import init_owner_query_engine_without_sunit
from configs.query_engine.tax_information import init_tax_query_engine
from configs.query_engine.tax_information_without_sunit import init_tax_query_engine_without_sunit
from configs.supabase import run_websocket_listener
from exceptions import APIException
from libs.MissiveAPI import MissiveAPI
from middlewares.jwt_middleware import require_authentication
from services.services import (
    extract_address_information,
    handle_match,
    search_service,
    more_search_service, get_conversation_data, get_conversation_summary,
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


owner_query_engine = init_owner_query_engine()
owner_query_engine_without_sunit = init_owner_query_engine_without_sunit()
tax_query_engine = init_tax_query_engine()
tax_query_engine_without_sunit = init_tax_query_engine_without_sunit()


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


@app.route("/fetch_property", methods=["GET"])
@require_authentication
def fetch_property():
    from cron.property import fetch_data
    thread = threading.Thread(target=fetch_data)
    thread.start()
    return jsonify({"message": "Data fetch started"}), 200


@app.route("/fetch_rental", methods=["GET"])
@require_authentication
def fetch_rental():
    from cron.rental import fetch_data
    thread = threading.Thread(target=fetch_data)
    thread.start()
    return jsonify({"message": "Data fetch started"}), 200


@app.route('/conversations', methods=['GET'])
def get_conversation():
    # Get parameters from the URL
    conversation_id = request.args.get('conversation_id')
    reference = request.args.get('reference')

    # Get teamId from the headers
    team_id = request.headers.get('X-Teams')
    env_team_id = os.getenv('TEAM_ID')

    if not env_team_id or env_team_id != team_id:
        return jsonify({'error': 'Unauthorized'}), 401

    # Check if conversation_id and reference are provided
    if not conversation_id:
        return jsonify({'error': 'Conversation ID is required'}), 400
    if not reference:
        return jsonify({'error': 'Reference is required'}), 400

    try:
        # Call the service functions to get conversation data and summary
        conversation_data = get_conversation_data(conversation_id, reference)
        print(conversation_data)
        # Check if the conversation data and summary exist
        if not conversation_data:
            return jsonify({'error': 'Error while getting user data'}), 404

        # Return the conversation data and summary
        return jsonify(
            conversation_data
        ), 200

    except Exception as e:
        # Handle any exceptions that occur during the process
        return jsonify({'error': str(e)}), 500


def start_mqtt():
    t = threading.Thread(target=run_websocket_listener)
    t.daemon = True
    t.start()


if __name__ == "__main__":
    start_mqtt()
    app.run(port=8080, host="0.0.0.0")
