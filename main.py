import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from configs.query_config import query_engine
from constants import ADDRESS_FOUND_MESSAGE, NO_INFO_MESSAGE
from middlewares.auth_middleware import require_authentication
from services.services import search_service

load_dotenv()

app = Flask(__name__)

key = os.environ.get("OPENAI_API_KEY")


@app.route("/query", methods=["POST"])
@require_authentication
def execute_query():
    data = request.get_json()
    query = data.get("query")
    if not query:
        return jsonify({"error": "No query provided"}), 400
    try:
        response = query_engine.query(query)
        return jsonify({"result": str(response)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/search", methods=["POST"])
@require_authentication
def search():
    query = request.json.get("query", "")

    closest_match = search_service(query)

    if not closest_match:
        return {"message": NO_INFO_MESSAGE.format(query)}, 200

    return {"message": ADDRESS_FOUND_MESSAGE.format(closest_match)}, 200


@app.route("/", methods=["GET"])
def health_check():
    return "ok"


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")
