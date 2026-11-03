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
        logger.info(f"[extract_address_information_with_llm] parsed an address: {bool(address)}")
        return address, sunit
    except Exception as e:
        print(f"An error occurred at extract_address_information_with_llm: {traceback.format_exc()}")
        logger.error(f"The address parser failed: {type(e).__name__}")
        return None, None
