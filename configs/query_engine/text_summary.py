from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI

from configs.cache_template import get_template_content_by_name

load_dotenv(override=True)
model = get_template_content_by_name("summary_model")
llm = OpenAI(model=model)


def generate_text_summary(summary_input, prompt=None):
    comments = [str(item) for item in summary_input]
    joined_comments = " ".join(comments)
    temp = f"{prompt}" + joined_comments
    return llm.complete(temp)
