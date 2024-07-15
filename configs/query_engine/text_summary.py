from loguru import logger
import os

from dotenv import load_dotenv

from configs.cache_template import get_template_content_by_name
from configs.database import Session
from llama_index.llms.openai import OpenAI

from models import LookupTemplate

load_dotenv(override=True)
key = os.environ.get("OPENAI_API_KEY")
session = Session()
model = get_template_content_by_name("summary_model")

llm_configs = session.query(LookupTemplate.content).filter(LookupTemplate.name == 'max_tokens').first()
try:
    max_tokens = int(llm_configs.content)
except (ValueError, AttributeError) as error:
    logger.error(f"Error: max_tokens is set incorrectly {llm_configs}, {error}. Aborting server startup.")
    exit(1)

llm = OpenAI(model=model, max_tokens=max_tokens)


def generate_text_summary(summary_input, prompt=None):
    comments = [str(item) for item in summary_input]
    joined_comments = " ".join(comments)
    return llm.complete(f"{joined_comments}\n\nSummarize in under 200 words: " + prompt)
