"""Tests for the SOC console REST API (E10-01, SCRUM-45)."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
from fastapi.testclient import TestClient

from thesis.api.app import HOST, create_app
from thesis.report.render import report_filename

SPECIAL_ID = "hp-ssh-01|2026-10-11T11:38:20+00:00"  # a real bundle id: carries '|' and ':'


def _row(
    bundle: str,
    *,
    strategy: str = "agentic",
    safety: str = "enforcing",
    sources: list[str] | None = None,
    emitted: bool = True,
    truth: str = "syn_flood",
    incident_type: str | None = "syn_flood",
) -> dict[str, object]:
    return {
        "bundle_id": bundle,
        "strategy": strategy,
        "safety": safety,
        "sources": sources if sources is not None else ["flows", "honeypot", "mqtt"],
        "repetition": 0,
        "ground_truth": truth,
        "emitted": emitted,
        "incident_type": incident_type,
        "confidence": 0.9 if emitted else None,
        "recommended_action": "rate_limit_source" if emitted else None,
        "severity": "high" if emitted else None,
        "affected_device": "iot-cam-01" if emitted else None,
        "evidence": ["a1"] if emitted else [],
    }


def _client(tmp: Path) -> TestClient:
    rows = [
        _row("b1"),  # C1, emitted
        _row("b2", emitted=False, incident_type=None),  # C1, withheld
        _row("b3", sources=["flows"]),  # C2 (single source) — must be filtered out
        {**_row("b1"), "repetition": 1},  # a second repetition — ignored (rep 0 only)
    ]
    results = tmp / "results.parquet"
    pq.write_table(pa.Table.from_pylist(rows), results)

    audit = tmp / "audit.jsonl"
    audit.write_text(
        json.dumps(
            {
                "bundle_id": "b1",
                "config_hash": "c",
                "repetition": 0,
                "node": "recommendation",
                "attempt": 1,
                "validator_outcome": "pass",
                "rejection_reason": None,
                "policy_action": "emit",
                "emitted": True,
                "call_ref": "c:b1:r0:recommendation",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    reports = tmp / "reports"
    reports.mkdir()
    (reports / "b1.md").write_text("# Incident b1\nThis is a recommendation. A human decides.\n")
    # A report written under the sanitised name the renderer uses for a real (':'/'|') bundle id.
    (reports / report_filename(SPECIAL_ID)).write_text("# special\nA human decides.\n")

    return TestClient(
        create_app(
            results_path=results,
            reports_dir=reports,
            audit_path=audit,
            db_path=tmp / "state.sqlite",
        )
    )


def test_incidents_returns_bundles_with_verdict_typed_fields(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.get("/incidents")
    assert resp.status_code == 200
    data = resp.json()
    ids = [i["bundle_id"] for i in data]
    assert ids == ["b1", "b2"]  # only C1 bundles, b3 (single source) filtered out
    b1 = next(i for i in data if i["bundle_id"] == "b1")
    assert b1["verdict"]["classification"]["incident_type"] == "syn_flood"  # Verdict shape
    assert b1["verdict"]["recommendation"]["recommended_action"] == "rate_limit_source"
    b2 = next(i for i in data if i["bundle_id"] == "b2")
    assert b2["verdict"] is None and b2["emitted"] is False  # withheld


def test_conditions_list_and_filter(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.get("/conditions").json() == ["C1", "C2"]  # from the fixture rows
    # The single-source flows bundle b3 is condition C2, not in the default C1 view.
    c2 = client.get("/incidents", params={"condition": "C2"}).json()
    assert [i["bundle_id"] for i in c2] == ["b3"]
    assert c2[0]["condition"] == "C2"
    assert client.get("/incidents", params={"condition": "C9"}).status_code == 404


def test_binds_to_localhost_only() -> None:
    assert HOST == "127.0.0.1"  # never 0.0.0.0 (§4, §6.8)


def test_the_only_non_get_route_is_the_decision_endpoint(tmp_path: Path) -> None:
    app = _client(tmp_path).app
    writes = set()
    for route in app.routes:
        methods = getattr(route, "methods", set()) or set()
        for method in methods:
            if method not in {"GET", "HEAD", "OPTIONS"}:
                writes.add((route.path, method))  # type: ignore[attr-defined]
    assert writes == {("/incidents/{bundle_id}/decision", "POST")}


def test_decision_is_stored_and_reflected(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.post("/incidents/b1/decision", json={"decision": "accept", "note": "looks right"})
    assert resp.status_code == 200
    assert resp.json()["decision"] == "accept"
    assert resp.json()["condition"] == "C1"  # defaults to the full agent
    # The decision now shows on the incident.
    assert client.get("/incidents/b1").json()["decision"] == "accept"


def test_decision_is_scoped_to_condition(tmp_path: Path) -> None:
    # The same bundle has a different recommendation per condition, so a decision is tied to the
    # condition it was made under. b1 is C1; b3 is the C2 (single-source) view.
    client = _client(tmp_path)
    client.post("/incidents/b1/decision", json={"decision": "accept"})
    client.post("/incidents/b3/decision", params={"condition": "C2"}, json={"decision": "reject"})
    assert client.get("/incidents/b1").json()["decision"] == "accept"
    assert client.get("/incidents/b3", params={"condition": "C2"}).json()["decision"] == "reject"
    # A decision made under one condition does not leak to another's view of a different bundle.
    assert client.get("/incidents/b1", params={"condition": "C1"}).json()["decision"] == "accept"


def test_decision_rejects_unknown_incident_and_bad_value(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.post("/incidents/nope/decision", json={"decision": "accept"}).status_code == 404
    assert client.post("/incidents/b1/decision", json={"decision": "maybe"}).status_code == 422
    # b3 is C2 only, so a decision under the default C1 is a 404 (not that incident under C1).
    assert client.post("/incidents/b3/decision", json={"decision": "accept"}).status_code == 404


def test_audit_and_report_endpoints(tmp_path: Path) -> None:
    client = _client(tmp_path)
    audit = client.get("/audit").json()
    assert len(audit) == 1 and audit[0]["validator_outcome"] == "pass"
    report = client.get("/reports/b1")
    assert report.status_code == 200 and "A human decides" in report.text
    assert client.get("/reports/missing").status_code == 404
    # A real bundle id (with ':' and '|') resolves to the renderer's sanitised filename.
    special = client.get(f"/reports/{SPECIAL_ID}")
    assert special.status_code == 200 and "A human decides" in special.text


def _demo_client(tmp_path: Path) -> TestClient:
    from datetime import UTC, datetime, timedelta

    from thesis.api.demo import AlertRow, BundleMeta

    rows = [{**_row("eb1"), "config_hash": "c"}, {**_row("eb2"), "config_hash": "c"}]
    results = tmp_path / "results.parquet"
    pq.write_table(pa.Table.from_pylist(rows), results)

    catalog = tmp_path / "demo_scenarios.yaml"
    catalog.write_text(
        "scenarios:\n"
        "  - id: demo-x\n"
        "    title: t\n"
        "    description: d\n"
        "    episode_id: ep-x\n"
        "    bundle_ids: null\n"
        "    attack_family: syn_flood\n"
        "    default_condition: C1\n"
        "    highlight: null\n",
        encoding="utf-8",
    )
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    meta = {
        bid: BundleMeta(
            bundle_id=bid,
            device="iot-cam-01",
            window_start=t0 + timedelta(seconds=i * 60),
            window_end=t0 + timedelta(seconds=i * 60 + 60),
            label="syn_flood",
            episode_id="ep-x",
            sources=["flows"],
            alert_ids=["a1"],
        )
        for i, bid in enumerate(["eb1", "eb2"])
    }
    alerts = {"a1": AlertRow("a1", "flows", t0 + timedelta(seconds=5), "syn_flood", 1.0, "sum", {})}
    return TestClient(
        create_app(
            results_path=results,
            reports_dir=tmp_path / "reports",
            audit_path=tmp_path / "audit.jsonl",
            db_path=tmp_path / "state.sqlite",
            call_log_path=tmp_path / "nolog.jsonl",
            scenarios_path=catalog,
            demo_bundle_meta=meta,
            demo_alert_index=alerts,
        )
    )


def test_demo_scenarios_list_and_events(tmp_path: Path) -> None:
    client = _demo_client(tmp_path)
    scenarios = client.get("/demo/scenarios").json()
    assert any(s["id"] == "demo-x" for s in scenarios)
    ev = client.get("/demo/scenarios/demo-x", params={"condition": "C1"}).json()
    assert ev["condition"] == "C1" and ev["window_seconds"] >= 0
    kinds = {e["kind"] for e in ev["events"]}
    assert {"bundle_formed", "verdict", "recommendation"} <= kinds
    assert {e["bundle_id"] for e in ev["events"]} == {"eb1", "eb2"}
    assert client.get("/demo/scenarios/nope").status_code == 404


def test_demo_live_requires_hosted_env(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    client = _demo_client(tmp_path)
    # the live run is gated: no hosted model configured -> 503, never a 500 or a hang.
    assert client.get("/demo/live/eb1/trace").status_code == 503
