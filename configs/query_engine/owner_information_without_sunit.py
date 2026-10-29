from loguru import logger

from configs.cache_template import get_template_content_by_name
from configs.llm import build_llm


def owner_query_engine_without_sunit(result):
    function_llm = build_llm("search_model", temperature=0.1)

    city_stats_text = get_template_content_by_name("search_context")
    prompt = f"{city_stats_text}\n{result}"

    human_readable_result = function_llm.complete(prompt)
    logger.info(
        f"[owner_query_engine_without_sunit] {result}: {human_readable_result}"
    )
    return human_readable_result
