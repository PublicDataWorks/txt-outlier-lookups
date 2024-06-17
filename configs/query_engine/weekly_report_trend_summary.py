import os

from dotenv import load_dotenv
from llama_index.core import PromptTemplate, SQLDatabase, VectorStoreIndex
from llama_index.core.indices.struct_store.sql_query import SQLTableRetrieverQueryEngine
from llama_index.core.objects import ObjectIndex, SQLTableNodeMapping, SQLTableSchema
from llama_index.llms.openai import OpenAI
from sqlalchemy import MetaData

from configs.cache_template import get_template_content_by_name
from llama_index.core import DocumentSummaryIndex
from llama_index.llms.openai import OpenAI

load_dotenv(override=True)
key = os.environ.get("OPENAI_API_KEY")


def query_from_documents(documents):
    text = get_template_content_by_name("sms_history_summary")

    summary_index = DocumentSummaryIndex.from_documents(documents)

    query_engine = summary_index.as_query_engine(llm=OpenAI(model="gpt-3.5-turbo"))

    summary = query_engine.query(text)

    return summary
