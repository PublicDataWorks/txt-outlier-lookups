from dotenv import load_dotenv
from flask import Flask, jsonify, request
from libs.MissiveAPI import MissiveAPI
from middlewares.auth_middleware import require_authentication
from services.services import search_service

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
    response, status = search_service(query)
    return jsonify(response), status


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")
