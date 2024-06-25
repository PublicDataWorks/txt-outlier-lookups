import logging
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
logger = logging.getLogger(__name__)


def generate_text_summary(summary_input):

    llm = OpenAI(model="gpt-4o")
    comments = [str(item) for item in summary_input]

    joined_comments = " ".join(comments)

    return llm.complete(f"{joined_comments}\n\nSummarize under 200 words:")
