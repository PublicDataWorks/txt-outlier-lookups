import logging
import os
import sys

from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI

from configs.cache_template import get_template_content_by_name

load_dotenv(override=True)
key = os.environ.get("OPENAI_API_KEY")

logging.basicConfig(stream=sys.stdout, level=logging.WARNING)


def owner_query_engine_without_sunit(result):
    model = get_template_content_by_name("search_model")

    function_llm = OpenAI(temperature=0.1, model=model, api_key=key)

    city_stats_text = get_template_content_by_name("search_context")
    prompt = f"{city_stats_text}\n{result}"

    human_readable_result = function_llm.complete(prompt)

    return human_readable_result
