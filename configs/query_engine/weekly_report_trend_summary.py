import logging
import os

from dotenv import load_dotenv
from llama_index.core import DocumentSummaryIndex
from llama_index.core.schema import Document
from llama_index.llms.openai import OpenAI

from configs.cache_template import get_template_content_by_name
from configs.database import Session
from models import LookupTemplate
from templates.templates import templates

load_dotenv(override=True)
key = os.environ.get("OPENAI_API_KEY")
session = Session()
logger = logging.getLogger(__name__)


def generate_report_summary(messages_history):
    try:
        lookup_template = session.query(LookupTemplate).filter_by(name="sms_history_summary").first()
        if lookup_template:
            text = lookup_template.content
        else:
            fallback_template = templates.get("sms_history_summary")
            if fallback_template:
                text = fallback_template
            else:
                logger.error(f"Error fetching backup template")
                return None
    except Exception as e:
        logger.error(f"Error fetching template from database: {e}")
        return None
    documents = []
    for ref, conversations in messages_history.items():
        conversation_text = "\n".join(
            [f"{msg['from_field']} to {msg['to_field']}: {msg['preview']}" for msg in conversations])
        metadata = {
            'reference': ref,
            'from_fields': list(set(msg['from_field'] for msg in conversations)),
            'to_fields': list(set(msg['to_field'] for msg in conversations))
        }
        doc = Document(
            text=conversation_text,
            metadata=metadata
        )
        documents.append(doc)
    summary_index = DocumentSummaryIndex.from_documents(documents)

    # Get model from template 
    model = get_template_content_by_name("summary_model")
    query_engine = summary_index.as_query_engine(llm=OpenAI(model=model))

    summary = query_engine.query(text)

    return summary
