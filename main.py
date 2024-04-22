from dotenv import load_dotenv
from flask import Flask, jsonify, request

from configs.query_config import query_engine
from libs.MissiveAPI import MissiveAPI
from middlewares.auth_middleware import require_authentication
from services.services import search_service
from utils.check_tax_status import check_tax_status

load_dotenv()

app = Flask(__name__)
missiveAPI = MissiveAPI()


@app.route("/", methods=["GET"])
def health_check():
    return "OK"


@app.route("/search", methods=["POST"])
# @require_authentication
def search():
    query = request.json.get("query", "")
    data, status = search_service(query)

    match status:
        case "NO_MATCH":
            return {"result": data}, 404
        case "AMBIGUOUS":
            return {"result": data}, 404
        case "MATCH":
            response = query_engine.query(data)
            return {"result": str(response)}, 200
        case _:
            return {"result": "Internal Server Error"}, 500


@app.route("/send-sms", methods=["POST"])
def test_send_sms():
    data = request.get_json()
    message = data.get("message")
    to_phone = data.get("to_phone")
    conversation_id = data.get("conversation_id", None)
    add_label_list = data.get("add_label_list", [])
    remove_label_list = data.get("remove_label_list", [])

    response = missiveAPI.send_sms(
        message, to_phone, conversation_id, add_label_list, remove_label_list
    )

    if response is None:
        return jsonify({"error": "Failed to send SMS."}), 500
    else:
        return jsonify({"message": "SMS sent successfully!"}), 200


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")
