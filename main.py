import os
import sys

import sentry_sdk
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from loguru import logger
from sentry_sdk.integrations.loguru import LoggingLevels, LoguruIntegration
from werkzeug.middleware.proxy_fix import ProxyFix

from configs.query_engine.owner_information import owner_query_engine
from exceptions import APIException
from libs.MissiveAPI import MissiveAPI
from services.services import (
    handle_match,
    process_statuses,
    search_service,
    warning_not_in_session,
)
from utils.address_normalizer import extract_latest_address
from utils.check_property_status import check_property_status

load_dotenv(override=True)

sentry_loguru = LoguruIntegration(
    level=LoggingLevels.INFO.value,        # Capture info and above as breadcrumbs
    event_level=LoggingLevels.ERROR.value  # Send errors as events
)

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DNS"),
    enable_tracing=True,
    integrations=[
        sentry_loguru
    ],
)

logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")

app = Flask(__name__)


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
            query=message, conversation_id=conversation_id, to_phone=to_phone
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
        address = extract_latest_address(
            messages=messages, conversation_id=conversation_id, to_phone=to_phone
        )

        if not address:
            logger.error("Couldn't parse address from history messages", messages)
            return (
                jsonify({"message": "Couldn't parse address from history messages"}),
                200,
            )

        query_result = owner_query_engine.query(address)
        if not 'result' in query_result.metadata:
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
            messages = missive_client.extract_preview_content(conversation_id=conversation_id)
            address = extract_latest_address(messages, conversation_id, to_phone)

            if not address:
                logger.error("Couldn't parse address from history messages", messages)
                return (
                    jsonify({"message": "Couldn't parse address from history messages"}),
                    200,
                )
            query_result = owner_query_engine.query(address)
            if not 'result' in query_result.metadata:
                logger.error(query_result)
            tax_status, rental_status = check_property_status(query_result)

            process_statuses(tax_status, rental_status, conversation_id, to_phone)
            return jsonify("Success"), 200

        else:
            warning_not_in_session(conversation_id=conversation_id,to_phone=to_phone)
            return (
                jsonify({"error": "There was no ADDRESS_LOOKUP_TAG, try again later"}),
                200,
            )

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        logger.exception("", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")
