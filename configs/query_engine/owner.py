import os

from dotenv import load_dotenv
from llama_index.core import PromptTemplate, SQLDatabase, VectorStoreIndex
from llama_index.core.indices.struct_store.sql_query import SQLTableRetrieverQueryEngine
from llama_index.core.objects import ObjectIndex, SQLTableNodeMapping, SQLTableSchema
from llama_index.llms.openai import OpenAI
from sqlalchemy import MetaData

from configs.database import engine

load_dotenv()
key = os.environ.get("OPENAI_API_KEY")

text = (
    "Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer. You can order the results by a relevant column to return the most interesting examples in the database."
    "Never query for all the columns from a specific table, only ask for a few relevant columns given the question."
    "ALWAYS FOLLOW THE GIVEN BELOW RULES."  # My change added here!
    "Pay attention to use only the column names that you can see in the schema description. Be careful to not query for columns that do not exist. Pay attention to which column is in which table. Also, qualify column names with the table name when needed. You are required to use the following format, each taking one line:"
    "Only query based on the first address you get from the prompt "
    "Question: Question here"
    "SQLQuery: SQL Query to run"
    "SQLResult: Result of the SQLQuery"
    "Answer: Final answer here"
    "Only use tables listed below."
    "{schema}"
    "Question: {query_str}"
    "SQLQuery: "
)
qa_prompt_tmpl = PromptTemplate(text)


metadata = MetaData(schema="address_lookup")
sql_database = SQLDatabase(
    engine,
    schema="address_lookup",
    include_tables=["mi_wayne_detroit"],
    metadata=metadata,
)
function_llm = OpenAI(temperature=0.5, model="gpt-3.5-turbo", api_key=key)

city_stats_text = (
    "This table gives information regarding the properties and owners of a "
    "given city where owner is the address of the owner as OWNER NAME AND taxdue is the tax due amount"
    "Always return owner column"
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

owner_query_engine = SQLTableRetrieverQueryEngine(
    sql_database, obj_index.as_retriever(similarity_top_k=1), llm=function_llm
)

owner_query_engine.update_prompts(
    {"sql_retriever:text_to_sql_prompt": qa_prompt_tmpl},
)
