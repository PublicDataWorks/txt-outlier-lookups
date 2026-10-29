from loguru import logger

from configs.database import Session
from configs.llm import build_llm
from models import LookupTemplate

session = Session()

llm_configs = session.query(LookupTemplate.content).filter(LookupTemplate.name == 'max_tokens').first()
try:
    max_tokens = int(llm_configs.content)
except (ValueError, AttributeError) as error:
    logger.error(f"Error: max_tokens is set incorrectly {llm_configs}, {error}. Aborting server startup.")
    exit(1)


def generate_text_summary(summary_input, prompt=None):
    comments = [str(item) for item in summary_input]
    joined_comments = " ".join(comments)
    temp = f"{prompt}" + joined_comments
    return build_llm("summary_model").complete(temp)

