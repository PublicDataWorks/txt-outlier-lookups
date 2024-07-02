import logging
import os

from dotenv import load_dotenv
from configs.database import Session
from llama_index.llms.openai import OpenAI

load_dotenv(override=True)
key = os.environ.get("OPENAI_API_KEY")
session = Session()
logger = logging.getLogger(__name__)

llm = OpenAI(model="gpt-4o")


def generate_text_summary(summary_input, prompt=None):
    comments = [str(item) for item in summary_input]
    joined_comments = " ".join(comments)
    return llm.complete(f"{joined_comments}\n\nSummarize under 200 words: The theme will be " + prompt)
