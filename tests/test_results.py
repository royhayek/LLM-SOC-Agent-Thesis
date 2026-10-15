"""Tests for the result-row schema and writer (E9-02, SCRUM-53)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from thesis.assemble.bundles import Bundle
from thesis.config import ExperimentConfig, Provenance, Safety, Strategy
from thesis.eval.results import build_row, call_totals, read_results, write_results
from thesis.eval.run import RunResult
from thesis.schema.alert import Source
from thesis.schema.verdict import Verdict

T0 = datetime(2026, 1, 1, tzinfo=UTC)
PROV = Provenance(
    model="llama",
    model_revision="rev-1",
    provider="deepinfra",
    temperature=0.6,
    top_p=0.9,
    max_tokens=250,
    seed=None,
    prompt_template_version="prompts-v1.0",
    graph_version="graph-v1.0",
)
VERDICT = Verdict.model_validate(
    {
        "classification": {"incident_type": "syn_flood", "confidence": 0.8},
        "recommendation": {"recommended_action": "rate_limit_source", "severity": "high"},
        "affected_device": "iot-cam-01",
        "evidence": ["f1"],
    }
)


def _bundle(label: str = "syn_flood", episode: str | None = "ep-1") -> Bundle:
    return Bundle(
        bundle_id="iot-cam-01|w",
        device="iot-cam-01",
        window_start=T0,
        window_end=T0 + timedelta(seconds=60),
        label=label,
        episode_id=episode,
        sources=("flows",),
        alerts=(),
    )


def _config(strategy: Strategy, safety: Safety) -> ExperimentConfig:
    return ExperimentConfig(
        sources=frozenset({Source.FLOWS}),
        strategy=strategy,
        safety=safety,
        provenance=None if strategy is Strategy.ML_CLASSIFIER else PROV,
    )


def _result(payload: object, strategy: Strategy) -> RunResult:
    return RunResult("iot-cam-01|w", "hash", 0, strategy.value, payload)


def test_row_has_the_required_non_null_fields(tmp_path: Path) -> None:
    config = _config(Strategy.PROMPT_ONLY, Safety.LOGGING_ONLY)
    row = build_row(
        _result(VERDICT, Strategy.PROMPT_ONLY),
        _bundle(),
        config,
        tokens_in=1200,
        tokens_out=180,
        latency_ms=4200.0,
    )
    n = write_results([row], tmp_path / "r.parquet")
    assert n == 1
    got = read_results(tmp_path / "r.parquet")[0]
    for field in (
        "config_hash",
        "model_revision",
        "prompt_template_version",
        "bundle_id",
        "episode_id",
        "ground_truth",
        "incident_type",
        "severity",
        "affected_device",
        "recommended_action",
        "confidence",
        "tokens_in",
        "tokens_out",
        "latency_ms",
    ):
        assert got[field] is not None, f"{field} is null"
    assert got["ground_truth"] == "syn_flood"
    assert got["recommended_action"] == "rate_limit_source"
    assert got["evidence"] == ["f1"]


def test_same_bundle_rep_across_conditions_shares_bundle_and_truth() -> None:
    bundle = _bundle()
    agentic = build_row(
        _result(None, Strategy.AGENTIC),
        bundle,
        _config(Strategy.AGENTIC, Safety.ENFORCING),
        tokens_in=0,
        tokens_out=0,
        latency_ms=0.0,
    )
    ml = build_row(
        _result(VERDICT, Strategy.ML_CLASSIFIER),
        bundle,
        _config(Strategy.ML_CLASSIFIER, Safety.LOGGING_ONLY),
        tokens_in=0,
        tokens_out=0,
        latency_ms=0.0,
    )
    assert agentic.bundle_id == ml.bundle_id
    assert agentic.ground_truth == ml.ground_truth


def test_withheld_result_has_null_predicted_fields() -> None:
    row = build_row(
        _result(None, Strategy.PROMPT_ONLY),
        _bundle(),
        _config(Strategy.PROMPT_ONLY, Safety.LOGGING_ONLY),
        tokens_in=1000,
        tokens_out=0,
        latency_ms=3000.0,
    )
    assert row.emitted is False
    assert row.incident_type is None and row.recommended_action is None


def test_baseline_a_row_has_sentinel_provenance() -> None:
    row = build_row(
        _result(VERDICT, Strategy.ML_CLASSIFIER),
        _bundle(),
        _config(Strategy.ML_CLASSIFIER, Safety.LOGGING_ONLY),
        tokens_in=0,
        tokens_out=0,
        latency_ms=0.0,
    )
    assert row.model_revision == "baseline-a-v1.0"  # non-null even without an LLM
    assert row.tokens_in == 0


def test_benign_bundle_has_empty_episode_id_not_null() -> None:
    row = build_row(
        _result(VERDICT, Strategy.ML_CLASSIFIER),
        _bundle(label="benign", episode=None),
        _config(Strategy.ML_CLASSIFIER, Safety.LOGGING_ONLY),
        tokens_in=0,
        tokens_out=0,
        latency_ms=0.0,
    )
    assert row.episode_id == ""


def test_call_totals_sum_over_calls() -> None:
    records = [
        {"tokens_in": 1000, "tokens_out": 100, "latency_ms": 2000.0},
        {"tokens_in": 1100, "tokens_out": 120, "latency_ms": 2500.0},
    ]
    assert call_totals(records) == (2100, 220, 4500.0)
