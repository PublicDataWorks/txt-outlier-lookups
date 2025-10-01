import json
import traceback

from llama_index.llms.openai import OpenAI
from loguru import logger

from configs.cache_template import get_template_content_by_name
from configs.settings import key, get_address_parser_prompt


def extract_address_information_with_llm(addresses):
    function_llm = OpenAI(
        temperature=0.1,
        model=get_template_content_by_name("search_model"),
        api_key=key,
        additional_kwargs={
            "response_format": {
                "type": "json_object"
            }
        }
    )
    try:
        response = function_llm.complete(get_address_parser_prompt(addresses))
        parsed_data = json.loads(response.text)
        address = parsed_data["address"]
        sunit = parsed_data["sunit"]
        logger.info(
            f"[extract_address_information_with_llm]: Extracted address info - address='{address}', sunit='{sunit}'"
        )
        return address, sunit
    except Exception as e:
        print(f"An error occurred at extract_address_information_with_llm: {traceback.format_exc()}. Data: {addresses}")
        logger.error(e)

        return None, None
