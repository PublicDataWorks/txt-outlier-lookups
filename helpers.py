import json
import traceback

from loguru import logger

from configs.llm import build_llm
from configs.settings import PARSE_FAILURE_REASONS, get_address_parser_prompt, get_parse_failure_reason_prompt


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


def classify_unparseable_text(text):
    try:
        # /search answers the Missive webhook only after this, and the reason is just a tag, so it
        # gets less time and fewer retries than the parser (llama-index defaults: 60 s, 3 retries).
        function_llm = build_llm(
            "search_model",
            temperature=0.1,
            timeout=20,
            max_retries=1,
            additional_kwargs={
                "response_format": {
                    "type": "json_object"
                }
            }
        )
        response = function_llm.complete(get_parse_failure_reason_prompt(text))
        reason = str(json.loads(response.text).get("reason")).strip().lower()
    except Exception as e:
        logger.error(f"Classifying a parse failure failed: {type(e).__name__}")
        return "unknown"
    # The reason goes to Sentry, so anything off the list could be the resident's own words. Unknown
    # is ours, not the model's: a run of them means the classifier is broken.
    return reason if reason in PARSE_FAILURE_REASONS else "unknown"
