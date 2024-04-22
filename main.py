import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from llama_index.core import SQLDatabase, VectorStoreIndex, get_response_synthesizer
from llama_index.core.indices.struct_store.sql_query import SQLTableRetrieverQueryEngine
from llama_index.core.objects import ObjectIndex, SQLTableNodeMapping, SQLTableSchema
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.llms.openai import OpenAI
from sqlalchemy import MetaData, text

from configs.database import engine
from configs.query_config import query_engine
from constants.messages import ADDRESS_FOUND_MESSAGE, NO_INFO_MESSAGE
from libs.MissiveAPI import MissiveAPI
from middlewares.auth_middleware import require_authentication
from services.services import search_service
from utils.check_tax_status import check_tax_status
from utils.map_keys_to_result import map_keys_to_result

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


load_dotenv()
key = os.environ.get("OPENAI_API_KEY")

metadata = MetaData(schema="address_lookup")
sql_database = SQLDatabase(
    engine, schema="address_lookup", include_tables=["mi_wayne"], metadata=metadata
)
function_llm = OpenAI(temperature=0.5, model="gpt-3.5-turbo", api_key=key)
city_stats_text = (
    "This table gives information regarding the properties and owners of a "
    "given city where owner is the address of the owner as OWNER NAME, RENTAL STATUS, taxamt is TAX DEBT in outstanding taxes according to the Wayne County Treasurer"
    "and tax_status listed as COMPLIANT/IN FORFEITURE/FORECLOSED by the Treasurer."
)
table_node_mapping = SQLTableNodeMapping(sql_database)
table_schema_objs = [
    (SQLTableSchema(table_name="mi_wayne", context_str=city_stats_text))
]
obj_index = ObjectIndex.from_objects(
    table_schema_objs,
    table_node_mapping,
    VectorStoreIndex,
)

# query_engine = SQLTableRetrieverQueryEngine(
#     sql_database, obj_index.as_retriever(similarity_top_k=1), llm=function_llm
# )
response_synthesizer = get_response_synthesizer()

query_engine = SQLTableRetrieverQueryEngine(
    sql_database,
    obj_index.as_retriever(similarity_top_k=1),
    llm=function_llm,
)


@app.route("/test", methods=["POST"])
def test():
    data = request.get_json()
    query = data.get("query")
    if not query:
        return jsonify({"error": "No query provided"}), 400
    try:
        response = query_engine.query(query)

        return jsonify({"result": str(check_tax_status(response))})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


missiveAPI = MissiveAPI()


@app.route("/test_send_sms", methods=["POST"])
def test_send_sms():
    data = request.get_json()
    message = data.get("message")
    to_phone = data.get("to_phone")
    conversation_id = data.get("conversation_id", None)
    label_list = data.get("label_list", [])

    response = missiveAPI.send_sms(message, to_phone, conversation_id, label_list)

    if response is None:
        return jsonify({"error": "Failed to send SMS."}), 500
    else:
        return jsonify({"message": "SMS sent successfully!"}), 200


if __name__ == "__main__":
    app.run(port=8080, debug=True)
