"""Tests for the Baseline B strategy (E8-04, SCRUM-71)."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from thesis.baselines.baseline_b import NODE, baseline_b_verdict
from thesis.obs import logging as obslog
from thesis.schema.verdict import Verdict

VIEW: dict[str, object] = {
    "device": "iot-cam-01",
    "sources": {"flows": "active"},
    "flows": {"count": 1},
}
VALID = json.dumps(
    {
        "classification": {"incident_type": "syn_flood", "confidence": 0.8},
        "recommendation": {"recommended_action": "rate_limit_source", "severity": "high"},
        "affected_device": "iot-cam-01",
        "evidence": ["f1"],
    }
)


class FakeClient:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls = 0
        self.nodes: list[str] = []

    def complete(
        self,
        prompt: str,
        *,
        node: str,
        bundle_id: str,
        config_hash: str,
        repetition: int,
        json_schema: dict[str, object] | None = None,
    ) -> str:
        self.calls += 1
        self.nodes.append(node)
        assert json_schema is None  # Baseline B has no constrained decoding
        return self.reply


def test_valid_completion_parses_into_verdict() -> None:
    client = FakeClient(VALID)
    result = baseline_b_verdict(VIEW, client=client, bundle_id="b", config_hash="c", repetition=0)
    assert isinstance(result, Verdict)
    assert result.recommendation.recommended_action.value == "rate_limit_source"


def test_exactly_one_call_with_the_prompt_only_node() -> None:
    client = FakeClient(VALID)
    baseline_b_verdict(VIEW, client=client, bundle_id="b", config_hash="c", repetition=0)
    assert client.calls == 1
    assert client.nodes == [NODE]


def test_parse_failure_returns_none_and_is_not_retried() -> None:
    client = FakeClient("not a verdict")
    result = baseline_b_verdict(VIEW, client=client, bundle_id="b", config_hash="c", repetition=0)
    assert result is None  # invalid output recorded as a result
    assert client.calls == 1  # never retried (no hidden safety layer)


# --- AC2: the call log carries the same model/revision the agent uses -------------------------
@contextmanager
def _server(reply: str) -> Iterator[str]:
    body = json.dumps(
        {
            "id": "x",
            "object": "chat.completion",
            "created": 0,
            "model": "m",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": reply},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
        }
    ).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a: object) -> None:
            return

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}/v1"
    finally:
        srv.shutdown()
        t.join()


def test_call_log_has_the_agents_model_and_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from thesis.baselines import baseline_b as bb
    from thesis.llm.client import LLMClient

    log_path = tmp_path / "llm_calls.jsonl"
    monkeypatch.setattr(
        bb, "render", lambda *a, **k: "prompt"
    )  # avoid needing the real template here
    import thesis.llm.client as client_mod

    monkeypatch.setattr(
        client_mod, "log_llm_call", lambda **kw: obslog.log_llm_call(**kw, path=log_path)
    )
    with _server(VALID) as base_url:
        client = LLMClient(
            model="shared-model", base_url=base_url, api_key="k", model_revision="rev-9"
        )
        baseline_b_verdict(VIEW, client=client, bundle_id="b", config_hash="c", repetition=0)
    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert record["model"] == "shared-model" and record["model_revision"] == "rev-9"
    assert record["node"] == NODE
