import asyncio
import os

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

from configs.query_engine.owner import owner_query_engine
from configs.query_engine.tax import tax_query_engine
from exceptions import APIException
from libs.MissiveAPI import MissiveAPI
from middlewares.auth_middleware import require_authentication
from services.services import (
    handle_match,
    process_statuses,
    search_service,
    warning_not_in_session,
)
from utils.address_normalizer import get_first_valid_normalized_address
from utils.check_house_status import check_house_status

load_dotenv()

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
    data = request.get_json()
    conversation_id = data.get("conversation", {}).get("id")
    phone = data.get("message", {}).get("from_field", {}).get("id")
    message = data.get("message", {}).get("preview")

    response, status = search_service(
        query=message, conversation_id=conversation_id, to_phone=phone
    )
    return jsonify(response), status


@app.route("/yes", methods=["POST"])
def yes():
    try:
        data = request.get_json()
        conversation_id = data.get("conversation", {}).get("id")
        to_phone = data.get("message", {}).get("from_field", {}).get("id")
        messages = missive_client.extract_preview_content(conversation_id)
        if messages is None:
            missive_client.send_sms_sync(
                "There was a problem getting message history, try again later",
                conversation_id=conversation_id,
                to_phone=to_phone,
            )

            return (
                jsonify(
                    {
                        "message": "There was a problem getting message history, try again later"
                    }
                ),
                200,
            )
        address = get_first_valid_normalized_address(messages)

        if address is None:
            missive_client.send_sms_sync(
                "Can't parse address from history messages",
                conversation_id=conversation_id,
                to_phone=to_phone,
            )
            return (
                jsonify({"message": "Can't parse address from history messages"}),
                200,
            )

        query_result = owner_query_engine.query(address.get("address_line_1"))
        asyncio.run(handle_match(query_result, conversation_id, to_phone))
        return jsonify({"message": "Success"}), 200
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/more", methods=["POST"])
def more():
    try:
        data = request.get_json()
        conversation_id = data.get("conversation", {}).get("id")
        to_phone = data.get("message", {}).get("from_field", {}).get("id")
        shared_labels = data.get("conversation", {}).get("shared_labels", [])
        shared_label_ids = [label.get("id") for label in shared_labels]

        if (
            shared_label_ids
            and os.environ.get("MISSIVE_LOOKUP_TAG_ID") in shared_label_ids
        ):
            messages = missive_client.extract_preview_content(conversation_id)
            if messages is None:
                missive_client.send_sms_sync(
                    "There was a problem getting message history, try again later",
                    conversation_id=conversation_id,
                    to_phone=to_phone,
                )

                return (
                    jsonify(
                        {
                            "message": "There was a problem getting message history, try again later"
                        }
                    ),
                    200,
                )
            address = get_first_valid_normalized_address(messages)

            if address is None:
                missive_client.send_sms_sync(
                    "Can't parse address from history messages",
                    conversation_id=conversation_id,
                    to_phone=to_phone,
                )
                return (
                    jsonify({"message": "Can't parse address from history messages"}),
                    200,
                )

            query_result = owner_query_engine.query(address.get("address_line_1"))
            tax_status, rental_status = check_house_status(query_result)

            asyncio.run(
                process_statuses(tax_status, rental_status, conversation_id, to_phone)
            )
            return jsonify("Success"), 200

        else:
            missive_client.send_sms_sync(
                "You are not currently in a lookup session, please initiate one before querying for more infomation.",
                conversation_id=conversation_id,
                to_phone=to_phone,
            )
            return (
                jsonify({"error": "There was no ADDRESS_LOOKUP_TAG, try again later"}),
                200,
            )

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0", debug=True)
