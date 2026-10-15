"""Tests for the one LLM client (E6-01, SCRUM-28).

A fake OpenAI-compatible server exercises retry, the output ceiling and logging without a real
model. The marker test against local Ollama is `slow`. These test the code around the model, never
its output quality.
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from thesis.llm import client as client_module
from thesis.llm.client import LLMClient, LLMError
from thesis.obs import logging as obslog
from thesis.reduce.check_tokens import TokenCeilingError


def _completion_body(content: str, completion_tokens: int = 3) -> dict[str, object]:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": completion_tokens,
            "total_tokens": 5 + completion_tokens,
        },
    }


@contextmanager
def _fake_server(responses: list[tuple[int, dict[str, object]]]) -> Iterator[str]:
    """Serve the queued (status, body) responses in order at a throwaway OpenAI-compatible URL."""
    queue = list(responses)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            status, body = queue.pop(0) if queue else (500, {"error": "no response queued"})
            payload = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args: object) -> None:  # silence the test server
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/v1"
    finally:
        server.shutdown()
        thread.join()


def _client(base_url: str, **overrides: object) -> LLMClient:
    return LLMClient(
        model="test-model", base_url=base_url, api_key="test-key", backoff_base_s=0.01, **overrides
    )


def test_retries_on_429_then_returns_the_third_response() -> None:
    responses = [
        (429, {"error": {"message": "rate limited"}}),
        (429, {"error": {"message": "rate limited"}}),
        (200, _completion_body("recovered")),
    ]
    waits: list[float] = []
    with _fake_server(responses) as base_url:
        client = _client(base_url)
        client.sleep = waits.append
        out = client.complete("hi", node="n", bundle_id="b", config_hash="c", repetition=0)
    assert out == "recovered"
    assert waits == [0.01, 0.02]  # increasing backoff, two retries before the third attempt


def test_gives_up_after_the_attempt_cap() -> None:
    responses = [(429, {"error": {"message": "rate limited"}})] * 10
    with _fake_server(responses) as base_url:
        client = _client(base_url, max_attempts=3)
        client.sleep = lambda _s: None
        with pytest.raises(LLMError):
            client.complete("hi", node="n", bundle_id="b", config_hash="c", repetition=0)


def test_output_over_the_ceiling_raises_and_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_path = tmp_path / "llm_calls.jsonl"
    monkeypatch.setattr(
        client_module, "log_llm_call", lambda **kw: obslog.log_llm_call(**kw, path=log_path)
    )
    long_completion = " ".join(["telemetry"] * 300)  # ~300 tokens, over the 250 ceiling
    with _fake_server(
        [(200, _completion_body(long_completion, completion_tokens=300))]
    ) as base_url:
        client = _client(base_url)
        with pytest.raises(TokenCeilingError):
            client.complete("hi", node="n", bundle_id="b", config_hash="c", repetition=0)
    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert record["parse_outcome"] == "output_ceiling_exceeded"


def test_one_record_with_all_twelve_fields_is_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_path = tmp_path / "llm_calls.jsonl"
    monkeypatch.setattr(
        client_module, "log_llm_call", lambda **kw: obslog.log_llm_call(**kw, path=log_path)
    )
    with _fake_server([(200, _completion_body("ok"))]) as base_url:
        client = _client(base_url, model_revision="rev-abc")
        client.complete("hello", node="evidence", bundle_id="bun-1", config_hash="h", repetition=2)
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert set(record) == {
        "node",
        "model",
        "model_revision",
        "tokens_in",
        "tokens_out",
        "latency_ms",
        "prompt",
        "completion",
        "parse_outcome",
        "config_hash",
        "bundle_id",
        "repetition",
    }
    assert record["node"] == "evidence"
    assert record["model_revision"] == "rev-abc"
    assert record["repetition"] == 2


def test_from_env_requires_base_url_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    with pytest.raises(LLMError):
        LLMClient.from_env()


@pytest.mark.slow
def test_marker_roundtrip_against_local_ollama() -> None:
    """The only reliable num_ctx check: a marker survives a round-trip through local Ollama."""
    if not os.environ.get("LLM_BASE_URL"):
        pytest.skip("LLM_BASE_URL not set; needs local Ollama")
    marker = "ALPHA-7731-OMEGA"
    client = LLMClient.from_env()
    out = client.complete(
        f"Repeat this token exactly and nothing else: {marker}",
        node="marker",
        bundle_id="marker-test",
        config_hash="marker",
        repetition=0,
    )
    assert marker in out
