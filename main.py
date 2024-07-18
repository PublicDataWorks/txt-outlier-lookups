import os
import sys
import threading
import traceback

import sentry_sdk
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required
from loguru import logger
from sentry_sdk.integrations.loguru import LoggingLevels, LoguruIntegration
from werkzeug.middleware.proxy_fix import ProxyFix
from urllib.parse import unquote

from configs.cache_template import app

from configs.query_engine.owner_information import init_owner_query_engine
from configs.query_engine.owner_information_without_sunit import (
    init_owner_query_engine_without_sunit,
)
from configs.query_engine.tax_information import init_tax_query_engine
from configs.query_engine.tax_information_without_sunit import (
    init_tax_query_engine_without_sunit,
)
from configs.supabase import run_websocket_listener
from exceptions import APIException
from libs.MissiveAPI import MissiveAPI
from middlewares.jwt_middleware import require_authentication
from services.analytics.service import AnalyticsService
from services.services import (
    extract_address_information,
    extract_address_messages_from_supabase,
    get_conversation_data,
    handle_match,
    more_search_service,
    search_service, update_author_and_missive,
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

SUMMARY_CONVO_SIDEBAR_ADDRESS = os.getenv('SUMMARY_CONVO_SIDEBAR_ADDRESS')
if not SUMMARY_CONVO_SIDEBAR_ADDRESS:
    logger.error("Error: SUMMARY_CONVO_SIDEBAR_ADDRESS is not set. Aborting server startup.")
    sys.exit(1)

JWT_SECRET = os.getenv('JWT_SECRET')
if not JWT_SECRET:
    logger.error("Error: JWT_SECRET is not set. Aborting server startup.")
    sys.exit(1)

app.config['SECRET_KEY'] = JWT_SECRET
jwt = JWTManager(app)

CORS(app, origins=[SUMMARY_CONVO_SIDEBAR_ADDRESS])
os.makedirs('cache', exist_ok=True)

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


@app.before_request
def log_request_info():
    logger.info(f'Request: {request.path}')


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
        print(f"An error occurred at lookup /search: {traceback.format_exc()}")
        logger.error(e)
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
            extra_messages = extract_address_messages_from_supabase(to_phone)
            normalized_address = extract_latest_address(
                messages=extra_messages,
                conversation_id=conversation_id,
                to_phone=to_phone,
            )

        if not normalized_address:
            print(f"An error occurred at lookup /yes: {traceback.format_exc()}")
            logger.error("Couldn't parse address from history messages", messages)
            return (
                jsonify({"message": "Couldn't parse address from history messages"}),
                500,
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
        print(f"An error occurred at lookup /yes: {traceback.format_exc()}")
        logger.error(e)
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
        print(f"An error occurred at lookup /more: {traceback.format_exc()}")
        logger.error("", e)
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


@app.route("/weekly_report", methods=["GET"])
@require_authentication
def send_weekly_report():
    analytics = AnalyticsService()
    analytics.send_weekly_report()
    return jsonify({"message": "Weekly report sent"}), 200


@app.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    reference = request.args.get('reference')

    if not conversation_id:
        return jsonify({'error': 'Conversation ID is required'}), 400
    if not reference:
        return jsonify({'error': 'Reference is required'}), 400

    if not reference.strip().startswith('+'):
        reference = '+' + reference

    try:
        conversation_data = get_conversation_data(conversation_id, reference)
        if not conversation_data:
            return jsonify({'error': 'Error while getting user data'}), 404

        return jsonify(
            conversation_data
        ), 200

    except Exception as e:
        logger.error({'error occurred at getting conversation summary /conversations/<conversation_id>': traceback.format_exc()})
        return jsonify({'error': str(e)}), 500


@app.route('/contacts/<phone_number>', methods=['PATCH'])
def update_contact(phone_number):
    phone_number = unquote(phone_number)

    if not phone_number.strip().startswith('+'):
        phone_number = '+' + phone_number

    update_data = request.json

    if not update_data:
        return jsonify({'error': 'Update data is required'}), 400

    email = update_data.get('email')
    zipcode = update_data.get('zipcode')

    if email is None and zipcode is None:
        return jsonify({'error': 'At least one of email or zipcode is required'}), 400

    result, status_code = update_author_and_missive(phone_number, email, zipcode)

    return jsonify(result), status_code


def start_mqtt():
    t = threading.Thread(target=run_websocket_listener)
    t.daemon = True
    t.start()


if __name__ == "__main__":
    start_mqtt()
    app.run(port=8080, host="0.0.0.0")
