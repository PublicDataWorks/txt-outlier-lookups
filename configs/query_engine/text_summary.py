import os

from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI
from loguru import logger

from configs.cache_template import get_template_content_by_name
from configs.database import Session
from models import LookupTemplate

load_dotenv(override=True)
session = Session()
model = get_template_content_by_name("summary_model")

llm_configs = session.query(LookupTemplate.content).filter(LookupTemplate.name == 'max_tokens').first()
try:
    max_tokens = int(llm_configs.content)
except (ValueError, AttributeError) as error:
    logger.error(f"Error: max_tokens is set incorrectly {llm_configs}, {error}. Aborting server startup.")
    exit(1)

llm = OpenAI(model=model)


def generate_text_summary(summary_input, prompt=None):
    comments = [str(item) for item in summary_input]
    joined_comments = " ".join(comments)
    temp = f"{prompt}" + joined_comments
    return llm.complete(temp)

