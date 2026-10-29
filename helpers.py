import json
import traceback

from loguru import logger

from configs.llm import build_llm
from configs.settings import get_address_parser_prompt


def extract_address_information_with_llm(addresses):
    function_llm = build_llm(
        "search_model",
        temperature=0.1,
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
            f"[extract_address_information_with_llm] address: '{address}', sunit: '{sunit}'"
        )
        return address, sunit
    except Exception as e:
        logger.error(
            f"An error occurred at extract_address_information_with_llm {e}: {traceback.format_exc()}. Data: {addresses}"
        )
        return None, None
