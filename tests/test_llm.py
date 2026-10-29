import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from llama_index.core import Settings

from configs.cache_template import get_template_content_by_name
from configs.llm import EMBEDDING_MODEL, build_llm
from configs.query_engine.weekly_report_trend_summary import generate_report_summary

REPO_ROOT = Path(__file__).resolve().parent.parent


class FakeOpenAIHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requested_models.append(body["model"])
        if "temperature" in body and body.get("reasoning_effort", "none") != "none":
            self.reply(400, {"error": {"message": "temperature is not supported with reasoning effort"}})
        elif self.path.endswith("/embeddings"):
            inputs = body["input"] if isinstance(body["input"], list) else [body["input"]]
            self.reply(200, {
                "object": "list",
                "model": body["model"],
                "data": [{"object": "embedding", "index": i, "embedding": [0.01] * 1536} for i in range(len(inputs))],
                "usage": {"prompt_tokens": 1, "total_tokens": 1},
            })
        else:
            self.reply(200, {
                "id": "chatcmpl-test", "object": "chat.completion", "created": 0, "model": body["model"],
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "summary"},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            })

    def reply(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def fake_openai(monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAIHandler)
    server.requested_models = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    api_base = f"http://127.0.0.1:{server.server_address[1]}/v1"
    # The env var covers llms built during the test; the Settings defaults were built at import, so they
    # are redirected directly. Otherwise a request could reach the real OpenAI API with a real .env key.
    monkeypatch.setenv("OPENAI_API_BASE", api_base)
    monkeypatch.setattr(Settings.llm, "api_base", api_base)
    monkeypatch.setattr(Settings.embed_model, "api_base", api_base)
    yield server
    server.shutdown()


def test_build_llm_uses_model_from_template():
    with patch("configs.llm.get_template_content_by_name", return_value="gpt-4o-mini"):
        llm = build_llm("search_model", temperature=0.1)

    assert (llm.model, llm.temperature) == ("gpt-4o-mini", 0.1)


def test_build_llm_turns_reasoning_off():
    with patch("configs.llm.get_template_content_by_name", return_value="gpt-6-luna"):
        llm = build_llm("search_model")

    assert llm.reasoning_effort == "none"


def test_build_llm_rejects_unknown_model():
    with patch("configs.llm.get_template_content_by_name", return_value="gpt-6-luna-typo"):
        with pytest.raises(ValueError, match="Unknown model"):
            build_llm("search_model")


def test_library_default_llm_is_the_summary_model():
    assert Settings.llm.model == get_template_content_by_name("summary_model")


def test_library_default_embedding_is_pinned():
    assert Settings.embed_model.model_name == EMBEDDING_MODEL


def test_weekly_report_only_calls_configured_models(fake_openai):
    messages_history = {
        f"ref-{i}": [{"from_field": "+15555550100", "to_field": "+15555550101", "preview": f"message {i}",
                      "sender_name": "Staff", "sender_email": "staff@example.com"}]
        for i in range(3)
    }
    with patch("configs.query_engine.weekly_report_trend_summary.session") as mock_session, \
            patch("configs.llm.get_template_content_by_name", return_value="gpt-6-luna"):
        mock_session.query.return_value.filter_by.return_value.first.return_value = MagicMock(content="Summarize")
        generate_report_summary(messages_history)

    assert set(fake_openai.requested_models) == {"gpt-6-luna", EMBEDDING_MODEL}


def test_openai_llms_are_only_built_in_configs_llm():
    sources = [
        path for path in REPO_ROOT.rglob("*.py")
        if not {".venv", "venv", "tests"} & set(path.relative_to(REPO_ROOT).parts)
    ]
    direct = [str(path.relative_to(REPO_ROOT)) for path in sources if "OpenAI(" in path.read_text()]

    assert direct == ["configs/llm.py"]
