import os

from dotenv import load_dotenv
from llama_index.core import SQLDatabase, VectorStoreIndex
from llama_index.core.indices.struct_store.sql_query import SQLTableRetrieverQueryEngine
from llama_index.core.objects import ObjectIndex, SQLTableNodeMapping, SQLTableSchema
from llama_index.llms.openai import OpenAI
from sqlalchemy import MetaData

from .database import engine

load_dotenv()
key = os.environ.get("OPENAI_API_KEY")

metadata = MetaData(schema="address_lookup")
sql_database = SQLDatabase(
    engine,
    schema="address_lookup",
    include_tables=["mi_wayne_detroit"],
    metadata=metadata,
)
function_llm = OpenAI(temperature=0.2, model="gpt-3.5-turbo", api_key=key)
city_stats_text = (
    "This table gives information regarding the properties and owners of a "
    "given city where owner is the address of the owner as OWNER NAME, RENTAL STATUS, taxamt is TAX DEBT in "
    "outstanding taxes according to the Wayne County Treasurer"
    "and tax_status listed as COMPLIANT/IN FORFEITURE/FORECLOSED by the Treasurer."
    "Always return owner, taxamt, tax_status columns"
)
table_node_mapping = SQLTableNodeMapping(sql_database)
table_schema_objs = [
    (SQLTableSchema(table_name="mi_wayne_detroit", context_str=city_stats_text))
]
obj_index = ObjectIndex.from_objects(
    table_schema_objs,
    table_node_mapping,
    VectorStoreIndex,
)

query_engine = SQLTableRetrieverQueryEngine(
    sql_database, obj_index.as_retriever(similarity_top_k=1), llm=function_llm
)
