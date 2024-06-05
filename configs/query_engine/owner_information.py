import os

from dotenv import load_dotenv
from llama_index.core import PromptTemplate, SQLDatabase, VectorStoreIndex
from llama_index.core.indices.struct_store.sql_query import SQLTableRetrieverQueryEngine
from llama_index.core.objects import ObjectIndex, SQLTableNodeMapping, SQLTableSchema
from llama_index.llms.openai import OpenAI
from sqlalchemy import MetaData

from configs.cache_template import get_template_content_by_name
from configs.database import engine

load_dotenv(override=True)
key = os.environ.get("OPENAI_API_KEY")


def init_owner_query_engine():
    text = get_template_content_by_name("search_prompt")
    qa_prompt_tmpl = PromptTemplate(text)

    metadata = MetaData(schema="address_lookup")
    sql_database = SQLDatabase(
        engine,
        schema="address_lookup",
        include_tables=["mi_wayne_detroit"],
        metadata=metadata,
    )
    function_llm = OpenAI(temperature=0.1, model="gpt-3.5-turbo", api_key=key)

    city_stats_text = get_template_content_by_name("search_context_with_sunit")

    table_node_mapping = SQLTableNodeMapping(sql_database)
    table_schema_objs = [(SQLTableSchema(table_name="mi_wayne_detroit", context_str=city_stats_text))]
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

    return owner_query_engine
