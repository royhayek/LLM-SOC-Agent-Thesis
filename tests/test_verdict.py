"""Tests for the verdict schema and constrained decoding (E7-01, SCRUM-33)."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from thesis.llm.client import LLMClient
from thesis.schema.verdict import ACTION_IDS, Action, Verdict, verdict_json_schema

_CATALOG = "knowledge/action_catalog.yaml"

VALID = {
    "classification": {"incident_type": "botnet", "confidence": 0.8},
    "recommendation": {"recommended_action": "isolate_device", "severity": "high"},
    "affected_device": "iot-cam-01",
    "evidence": ["flow-1", "flow-2"],
}


def test_valid_verdict_parses() -> None:
    v = Verdict.model_validate(VALID)
    assert v.classification.incident_type.value == "botnet"
    assert v.recommendation.recommended_action.value == "isolate_device"
    assert v.evidence == ["flow-1", "flow-2"]  # evidence field is present (never removed, §4.4)


def test_action_not_in_catalog_is_rejected_naming_the_field() -> None:
    bad = {**VALID, "recommendation": {"recommended_action": "nuke_it", "severity": "high"}}
    with pytest.raises(ValidationError) as exc:
        Verdict.model_validate(bad)
    assert "recommended_action" in str(exc.value)


def test_action_enum_is_generated_from_the_catalog() -> None:
    catalog = yaml.safe_load(open(_CATALOG, encoding="utf-8"))  # noqa: SIM115
    catalog_ids = [a["id"] for a in catalog["actions"]]
    assert list(ACTION_IDS) == catalog_ids
    assert sorted(m.value for m in Action) == sorted(catalog_ids)


def test_json_schema_enumerates_the_actions() -> None:
    schema = verdict_json_schema()
    action_enum = schema["$defs"]["Action"]["enum"]  # type: ignore[index]
    assert sorted(action_enum) == sorted(ACTION_IDS)


def _completion(content: str) -> dict[str, object]:
    return {
        "id": "x",
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
        "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
    }


@contextmanager
def _capturing_server(reply: dict[str, object]) -> Iterator[tuple[str, list[dict[str, object]]]]:
    captured: list[dict[str, object]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            captured.append(body)
            payload = json.dumps(reply).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/v1", captured
    finally:
        server.shutdown()
        thread.join()


def test_client_requests_json_object_for_the_verdict() -> None:
    # ADR-0012 Option A: the Verdict schema is the on/off signal; the request is json_object, not a
    # json_schema the hosted model would reject. Conformance is enforced after decoding.
    with _capturing_server(_completion(json.dumps(VALID))) as (base_url, captured):
        client = LLMClient(model="test-model", base_url=base_url, api_key="k")
        client.complete(
            "classify",
            node="recommendation",
            bundle_id="b",
            config_hash="c",
            repetition=0,
            json_schema=verdict_json_schema(),
        )
    assert captured[0]["response_format"] == {"type": "json_object"}  # type: ignore[index]


def test_client_omits_response_format_when_unconstrained() -> None:
    with _capturing_server(_completion("free text")) as (base_url, captured):
        client = LLMClient(model="test-model", base_url=base_url, api_key="k")
        client.complete("hi", node="evidence", bundle_id="b", config_hash="c", repetition=0)
    assert "response_format" not in captured[0]
