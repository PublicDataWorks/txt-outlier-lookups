import os

from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.llms.openai.utils import openai_modelname_to_contextsize

from configs.cache_template import get_template_content_by_name

load_dotenv(override=True)
key = os.environ.get("OPENAI_API_KEY")

EMBEDDING_MODEL = "text-embedding-3-small"
# Only sent to reasoning models (gpt-5.x, gpt-6.x); gpt-4o-mini ignores it. Low keeps SMS replies quick.
REASONING_EFFORT = "low"


def build_llm(model_template_name, **kwargs):
    model = get_template_content_by_name(model_template_name)
    # llama-index only rejects an unknown model on its first request, so a typo in lookup_template would surface
    # mid-request (and address parsing swallows it). Checking here makes startup fail instead.
    openai_modelname_to_contextsize(model)
    return OpenAI(
        model=model,
        api_key=key,
        reasoning_effort=REASONING_EFFORT,
        **kwargs,
    )


# Any llama-index component built without an llm or embed_model silently uses the library default, which is
# still gpt-3.5-turbo (shut down on 23 Oct 2026). That is how the weekly report broke, so the defaults are
# pinned here as well as passed explicitly.
Settings.llm = build_llm("summary_model")
Settings.embed_model = OpenAIEmbedding(model=EMBEDDING_MODEL, api_key=key)
