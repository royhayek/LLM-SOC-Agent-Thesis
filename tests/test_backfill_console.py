"""Tests for the console backfill: the deterministic replay logic, not any model output."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from thesis.assemble.bundles import Bundle
from thesis.config import ExperimentConfig, Provenance, Safety, Source, Strategy, config_hash
from thesis.eval.backfill_console import (
    load_completions,
    render_reports,
    replay_audit,
)
from thesis.report.render import report_filename
from thesis.schema.alert import Alert, FlowDetail

T0 = datetime(2026, 1, 1, tzinfo=UTC)

_PROV = Provenance(
    model="m",
    model_revision="rev",
    provider="p",
    temperature=0.6,
    top_p=0.9,
    max_tokens=768,
    seed=None,
    prompt_template_version="prompts-v1.1",
    graph_version="graph-v1.0",
)


def _config(safety: Safety, strategy: Strategy = Strategy.AGENTIC) -> ExperimentConfig:
    return ExperimentConfig(
        sources=frozenset({Source("flows")}),
        strategy=strategy,
        safety=safety,
        provenance=None if strategy is Strategy.ML_CLASSIFIER else _PROV,
    )


def _bundle(bundle_id: str = "iot-cam-01|w") -> Bundle:
    alert = Alert(
        alert_id="f1",
        source="flows",
        ts=T0,
        subject_device="iot-cam-01",
        detector_score=0.9,
        detector_label="syn_flood",
        detector_name="flow_classifier",
        detail=FlowDetail(
            flow_start=T0,
            duration_s=1.0,
            src_ip="10.77.0.22",
            src_port=5,
            dst_ip="192.0.2.1",
            dst_port=80,
            protocol="tcp",
            packets_fwd=10,
            packets_bwd=0,
            bytes_fwd=600,
            bytes_bwd=0,
        ),
    )
    return Bundle(
        bundle_id=bundle_id,
        device="iot-cam-01",
        window_start=T0,
        window_end=T0 + timedelta(seconds=60),
        label="syn_flood",
        episode_id="ep-1",
        sources=("flows",),
        alerts=(alert,),
    )


def _classify(action_type: str = "syn_flood") -> str:
    return json.dumps(
        {
            "incident_type": action_type,
            "severity": "high",
            "affected_device": "iot-cam-01",
            "confidence": 0.8,
        }
    )


def _recommend(action: str = "rate_limit_source", evidence: list[str] | None = None) -> str:
    return json.dumps(
        {"recommended_action": action, "evidence_ids": ["f1"] if evidence is None else evidence}
    )


def test_load_completions_filters_noise_and_keeps_last(tmp_path: Path) -> None:
    log = tmp_path / "calls.jsonl"
    lines = [
        {
            "config_hash": "real",
            "bundle_id": "b",
            "node": "evidence",
            "repetition": 0,
            "parse_outcome": "ok",
            "completion": "first",
        },
        {
            "config_hash": "real",
            "bundle_id": "b",
            "node": "evidence",
            "repetition": 0,
            "parse_outcome": "ok",
            "completion": "last",
        },  # a resumed item: last wins
        {
            "config_hash": "other",
            "bundle_id": "b",
            "node": "evidence",
            "repetition": 0,
            "parse_outcome": "ok",
            "completion": "wrong-config",
        },  # filtered: not a real hash
        {
            "config_hash": "real",
            "bundle_id": "z",
            "node": "evidence",
            "repetition": 0,
            "parse_outcome": "ok",
            "completion": "wrong-bundle",
        },  # filtered: not an eval bundle
        {
            "config_hash": "real",
            "bundle_id": "b",
            "node": "recommendation",
            "repetition": 1,
            "parse_outcome": "ok",
            "completion": "wrong-rep",
        },  # filtered: repetition != 0
        {
            "config_hash": "real",
            "bundle_id": "b",
            "node": "recommendation",
            "repetition": 0,
            "parse_outcome": "output_ceiling_exceeded",
            "completion": "over-ceiling",
        },  # filtered
    ]
    log.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    out = load_completions({"real"}, {"b"}, log_path=log)
    assert out == {("real", "b", "evidence"): "last"}


def test_replay_audit_reconstructs_one_record_per_agentic_item() -> None:
    enforcing, logging_only = _config(Safety.ENFORCING), _config(Safety.LOGGING_ONLY)
    h_enf, h_log = config_hash(enforcing), config_hash(logging_only)
    by_hash = {h_enf: enforcing, h_log: logging_only}
    labels = {h_enf: "C1", h_log: "C5"}
    bundles = {"iot-cam-01|w": _bundle()}

    # A valid verdict passes under enforcing; an out-of-space action is would_reject under
    # logging_only (recorded, but emitted unchanged).
    completions = {
        (h_enf, "iot-cam-01|w", "classification"): _classify(),
        (h_enf, "iot-cam-01|w", "recommendation"): _recommend("rate_limit_source"),
        (h_log, "iot-cam-01|w", "classification"): _classify(),
        (h_log, "iot-cam-01|w", "recommendation"): _recommend("rate_limit_source"),
    }
    records = replay_audit(by_hash, labels, completions, bundles)
    assert len(records) == 2  # one per (agentic condition, bundle)
    by_condition = {r.config_hash: r for r in records}
    assert by_condition[h_enf].validator_outcome == "pass"
    assert by_condition[h_enf].policy_action == "emit"
    assert by_condition[h_log].validator_outcome == "pass"
    assert by_condition[h_log].policy_action == "not_applied"
    assert all(r.attempt == 1 for r in records)  # the frozen policy: one attempt


def test_replay_audit_skips_items_with_no_logged_calls() -> None:
    enforcing = _config(Safety.ENFORCING)
    h = config_hash(enforcing)
    bundles = {"iot-cam-01|w": _bundle()}
    # Only node 2 was logged (node 3 missing) → no audit record, like a mid-graph parse failure.
    completions = {(h, "iot-cam-01|w", "classification"): _classify()}
    assert replay_audit({h: enforcing}, {h: "C1"}, completions, bundles) == []


def test_render_reports_writes_a_report_per_bundle(tmp_path: Path) -> None:
    c1 = _config(Safety.ENFORCING)
    c1_hash = config_hash(c1)
    bundles = {"iot-cam-01|w": _bundle("iot-cam-01|w"), "hp|w": _bundle("hp|w")}
    rows = [
        {  # emitted → a full report
            "config_hash": c1_hash,
            "bundle_id": "iot-cam-01|w",
            "emitted": True,
            "incident_type": "syn_flood",
            "confidence": 0.8,
            "recommended_action": "rate_limit_source",
            "severity": "high",
            "affected_device": "iot-cam-01",
            "evidence": ["f1"],
        },
        {  # withheld → a stub
            "config_hash": c1_hash,
            "bundle_id": "hp|w",
            "emitted": False,
            "incident_type": None,
            "confidence": None,
            "recommended_action": None,
            "severity": None,
            "affected_device": None,
            "evidence": [],
        },
    ]
    findings = {
        "source_findings": [{"source": "flows", "summary": "syn flood", "evidence_ids": ["f1"]}],
        "cross_source": "flood from one host",
        "candidate_hypotheses": [],
        "missing_evidence": [],
    }
    completions = {(c1_hash, "iot-cam-01|w", "evidence"): json.dumps(findings)}
    full, stub = render_reports(c1_hash, rows, completions, bundles, out_dir=tmp_path)
    assert (full, stub) == (1, 1)
    # Both incidents resolve to a file under the sanitised name the API reads.
    assert (tmp_path / report_filename("iot-cam-01|w")).exists()
    stub_text = (tmp_path / report_filename("hp|w")).read_text(encoding="utf-8")
    assert "No verdict was emitted" in stub_text and "nothing is executed" in stub_text
