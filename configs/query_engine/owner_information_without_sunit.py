import os

from dotenv import load_dotenv
from llama_index.core import PromptTemplate, SQLDatabase, VectorStoreIndex
from llama_index.core.indices.struct_store.sql_query import SQLTableRetrieverQueryEngine
from llama_index.core.objects import ObjectIndex, SQLTableNodeMapping, SQLTableSchema
from llama_index.llms.openai import OpenAI
from sqlalchemy import MetaData

from configs.database import engine

load_dotenv(override=True)
key = os.environ.get("OPENAI_API_KEY")

text = (
    "Given an input question, first create a syntactically correct {dialect} query to run, then look at the results "
    "of the query and return the answer. You can order the results by a relevant column to return the most "
    "interesting examples in the database."
    "Never query for all the columns from a specific table, only ask for a few relevant columns given the question."
    "ALWAYS FOLLOW THE GIVEN BELOW RULES."  # My change added here!
    "Pay attention to use only the column names that you can see in the schema description. Be careful to not query "
    "for columns that do not exist. Pay attention to which column is in which table. Also, qualify column names with "
    "the table name when needed. You are required to use the following format, each taking one line:"
    "Address will follow the format of a number followed by a street name"
    "If the properties is not a rental then omit that from the result"
    "If rental_status value is 'IS NOT' then must hide rental status from the result"
    "Avoid showing anything about rental status like 'It is not registered as a residential rental property'"
    "Question: Question here"
    "SQLQuery: SQL Query to run"
    "SQLResult: Result of the SQLQuery"
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
    include_tables=["mi_wayne_detroit", "residential_rental_registrations"],
    metadata=metadata,
)
function_llm = OpenAI(temperature=0.1, model="gpt-4", api_key=key)
city_stats_text = (
    "The mi_wayne_detroit table gives information regarding the properties and owners of a "
    "given city where owner is the name of the owner as OWNER NAME AND tax_due is the tax debt amount"
    "tax_status is the tax status of the place and rental status is the rental status"
    "the table residential_rental_registrations contains list of all rental properties in mi_wayne_detroit."
    "Write a query follow exactly this format, DO NOT change anything except for the query value"
    "SELECT mi_wayne_detroit.owner, CASE WHEN residential_rental_registrations.lat IS NOT NULL THEN 'IS' ELSE 'IS NOT' END AS rental_status, "
    "mi_wayne_detroit.tax_due, mi_wayne_detroit.tax_status FROM mi_wayne_detroit"
    "LEFT JOIN residential_rental_registrations ON ST_DWithin( mi_wayne_detroit.wkb_geometry, residential_rental_registrations.wkb_geometry , 0.001) and strict_word_similarity( mi_wayne_detroit.address, residential_rental_registrations.street_num || ' ' || residential_rental_registrations.street_name) > 0.8"
    "WHERE mi_wayne_detroit.address ILIKE 'query_value%'"
    "If rental_status value is 'IS NOT' then must hide rental status from the result"
    "Avoid showing anything about rental status like 'It is not registered as a residential rental property'"
    "or 'The property is not registered as a residential rental.' or similar not rental status"
    "Always return mi_wayne_detroit.owner, mi_wayne_detroit.tax debt and mi_wayne_detroit.tax"
    "Address will follow the format of a number followed by a street name"
    "Do not use keywords like 'yes' or 'more' as query value"
)
table_node_mapping = SQLTableNodeMapping(sql_database)
table_schema_objs = [(SQLTableSchema(table_name="mi_wayne_detroit", context_str=city_stats_text))]
obj_index = ObjectIndex.from_objects(
    table_schema_objs,
    table_node_mapping,
    VectorStoreIndex,
)

owner_query_engine_without_sunit = SQLTableRetrieverQueryEngine(
    sql_database, obj_index.as_retriever(similarity_top_k=1), llm=function_llm
)

owner_query_engine_without_sunit.update_prompts(
    {"sql_retriever:text_to_sql_prompt": qa_prompt_tmpl},
)
