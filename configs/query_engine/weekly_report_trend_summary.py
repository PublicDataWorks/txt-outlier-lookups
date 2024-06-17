import os
from models import LookupTemplate

from dotenv import load_dotenv
from configs.database import Session
from templates.templates import templates
from llama_index.core import DocumentSummaryIndex
from llama_index.llms.openai import OpenAI
from llama_index.core.schema import Document

load_dotenv(override=True)
key = os.environ.get("OPENAI_API_KEY")
session = Session()


def query_from_documents(messages_history):
    text = ""
    try:
        lookup_template = session.query(LookupTemplate).filter_by(name="sms_history_summary").first()
        if lookup_template:
            text = lookup_template.content
        else:
            fallback_template = templates.get("sms_history_summary")
            if fallback_template:
                text = fallback_template
    except Exception as e:
        print(f"Error fetching template from database: {e}")
        return None
    documents = [Document(doc_id=str(i), text=str(conversation)) for i, conversation in enumerate(messages_history.values())]

    summary_index = DocumentSummaryIndex.from_documents(documents)

    query_engine = summary_index.as_query_engine(llm=OpenAI(model="gpt-3.5-turbo"))

    summary = query_engine.query(text)

    return summary
