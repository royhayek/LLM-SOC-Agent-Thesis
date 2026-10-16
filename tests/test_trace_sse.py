"""Tests for the SSE reasoning-trace endpoint (E10-02, SCRUM-55)."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
from fastapi.testclient import TestClient

from thesis.api.app import create_app

C1_HASH = "c1hash"


def _c1_row(bundle: str) -> dict[str, object]:
    return {
        "bundle_id": bundle,
        "config_hash": C1_HASH,
        "strategy": "agentic",
        "safety": "enforcing",
        "sources": ["flows", "honeypot", "mqtt"],
        "repetition": 0,
        "ground_truth": "syn_flood",
        "emitted": True,
        "incident_type": "syn_flood",
        "confidence": 0.9,
        "recommended_action": "rate_limit_source",
        "severity": "high",
        "affected_device": "iot-cam-01",
        "evidence": ["a1"],
    }


def _call(bundle: str, node: str, completion: str) -> str:
    return json.dumps(
        {
            "bundle_id": bundle,
            "config_hash": C1_HASH,
            "repetition": 0,
            "node": node,
            "completion": completion,
        }
    )


def _client(tmp: Path) -> TestClient:
    results = tmp / "results.parquet"
    pq.write_table(pa.Table.from_pylist([_c1_row("b1"), _c1_row("b2")]), results)
    call_log = tmp / "llm_calls.jsonl"
    # b1 has a full recorded trace; b2 has none.
    call_log.write_text(
        "\n".join(
            [
                _call("b1", "recommendation", "action: rate_limit_source"),
                _call("b1", "evidence", "the flows show a SYN flood"),  # out of order on disk
                _call("b1", "classification", "this is syn_flood"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return TestClient(
        create_app(results_path=results, call_log_path=call_log, db_path=tmp / "state.sqlite")
    )


def _events(body: str) -> list[str]:
    return [ln[len("event: ") :] for ln in body.splitlines() if ln.startswith("event: ")]


def test_trace_streams_three_events_in_node_order(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/incidents/b1/trace")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert _events(resp.text) == ["evidence", "classify", "recommend"]  # ordered, not disk order
    # The evidence payload carries its completion and the untrusted flag for the frontend.
    first = json.loads(resp.text.split("data: ", 1)[1].split("\n", 1)[0])
    assert first["untrusted"] is True and "SYN flood" in first["completion"]


def test_trace_is_404_when_no_recorded_trace(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.get("/incidents/b2/trace").status_code == 404  # no calls recorded
    assert client.get("/incidents/unknown/trace").status_code == 404  # unknown incident
