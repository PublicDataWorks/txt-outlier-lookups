import os

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

from configs.query_engine.tax import tax_query_engine
from exceptions import APIException
from libs.MissiveAPI import MissiveAPI
from middlewares.auth_middleware import require_authentication
from services.services import search_service
from templates.sms import get_message
from utils.check_tax_status import check_tax_status

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


@app.route("/more", methods=["POST"])
def more():
    data = request.get_json()
    conversation_id = data.get("conversation", {}).get("id")
    phone = data.get("message", {}).get("from_field", {}).get("id")
    shared_labels = data.get("conversation", {}).get("shared_labels", [])
    shared_label_ids = [label.get("id") for label in shared_labels]

    if shared_label_ids and os.environ.get("MISSIVE_LOOKUP_TAG_ID") in shared_label_ids:
        messages = missive_client.extract_preview_content(conversation_id)
        query_result = tax_query_engine.query(str(messages))
        tax_status = check_tax_status(query_result)

        missive_client.send_sms(
            get_message(tax_status), conversation_id=conversation_id, to_phone=phone
        )
        return jsonify(tax_status), 200

    return "This request don't have LOOK_UP labels", 400


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0", debug=True)
