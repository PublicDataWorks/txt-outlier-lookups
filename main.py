from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from llama_index.core import PromptTemplate
from werkzeug.middleware.proxy_fix import ProxyFix

from configs.query_config import query_engine
from configs.query_engine.owner import owner_query_engine
from configs.query_engine.tax import tax_query_engine
from libs.MissiveAPI import MissiveAPI
from middlewares.auth_middleware import require_authentication
from middlewares.extract_data import extract_data
from services.services import search_service
from templates.sms import get_message
from utils.check_tax_status import check_tax_status

load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

missive_client = MissiveAPI()


@app.route("/", methods=["GET"])
def health_check():
    return "OK"


@app.route("/search", methods=["POST"])
def search():
    # @require_authentication
    data = request.get_json()
    conversation_id = data.get("conversation", {}).get("id")
    phone = data.get("message", {}).get("to_fields", [{}])[0].get("id")
    preview = data.get("message", {}).get("preview")

    print(f"Conversation ID: {conversation_id}, Phone: {phone}, Preview: {preview}")

    response, status = search_service(preview, conversation_id, phone)
    return jsonify(response), status


@app.route("/more", methods=["POST"])
def more():
    data = request.get_json()
    conversation_id = data.get("conversation", {}).get("id")
    to_fields = data.get("latest_message", {}).get("to_fields", [{}])
    to_phone = to_fields[0].get("phone") if to_fields else None

    messages = missive_client.extract_preview_content(conversation_id)
    tax_status = check_tax_status(str(messages))

    missive_client.send_sms(get_message(tax_status), to_phone, conversation_id)

    return jsonify(tax_status), 200


@app.route("/test", methods=["POST"])
def test():
    conversation_messages = [
        "34657 CHESTNUT ST",
        "You can save this number in your phone and text us anytime. Text REPORTER to let us know you want to talk to one or MENU to see popular reso",
        "459 CALVIN AVE",
        "Hello! This is TXT OUTLIER, a free info service from Detroit's Outlier Media. Text a word like LANDLORD or DTE to get an automatic reply or",
        "You can save this number in your phone and text us anytime. Text REPORTER to let us know you want to talk to one or MENU to see popular reso",
        "Detroit",
        "Thanks! Did not know you were going to get that... -KAL",
        "We don't have a quick answer for you. A reporter will follow up within 48 hours. Do you want to tell us a little more in the meantime? You c",
        "We'll follow up with you about that. Thanks for your patience.",
        "4138 BROOKSTONE DR",
        "You can save this number in your phone and text us anytime. Text REPORTER to let us know you want to talk to one or MENU to see popular reso",
        "Hey Kate 👋🏾 received ",
    ]

    response = tax_query_engine.query(str(conversation_messages))
    return {"result": conversation_messages}, 200


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")
