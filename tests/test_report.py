"""Tests for the results report generator (E9-11, SCRUM-118)."""

from __future__ import annotations

from pathlib import Path

from thesis.config import Provenance, config_hash
from thesis.eval.report import (
    cost_table,
    overall_table,
    reliability_table,
    write_outputs_md,
)
from thesis.eval.report import tests_table as render_tests_table  # aliased: pytest collects test*
from thesis.eval.run import load_conditions
from thesis.eval.stats import run_tests


def _prov() -> Provenance:
    return Provenance(
        model="m",
        model_revision="r",
        provider="p",
        temperature=0.6,
        top_p=0.9,
        max_tokens=768,
        seed=None,
        prompt_template_version="prompts-v1.1",
        graph_version="graph-v1.0",
    )


def _row(cfg: str, bundle: str, rep: int) -> dict[str, object]:
    return {
        "config_hash": cfg,
        "bundle_id": bundle,
        "repetition": rep,
        "ground_truth": "syn_flood",
        "emitted": True,
        "incident_type": "syn_flood",
        "recommended_action": "rate_limit_source",
        "evidence": [],
        "validator_outcome": "pass",
        "tokens_in": 1000,
        "tokens_out": 100,
        "latency_ms": 1500.0,
    }


def _rows() -> tuple[list[dict[str, object]], list]:
    conditions = load_conditions(_prov())
    rows: list[dict[str, object]] = []
    for cond in conditions:
        cfg = config_hash(cond)
        for b in ("b1", "b2"):
            for r in range(3):
                rows.append(_row(cfg, b, r))
    return rows, conditions


def test_overall_table_has_all_conditions_and_is_deterministic() -> None:
    rows, conditions = _rows()
    first = overall_table(rows, conditions)
    assert first == overall_table(rows, conditions)  # byte-identical on re-run
    for label in ("C1", "C2", "C5", "C6", "C7"):
        assert f"| {label} |" in first
    assert "DET F1" in first and "CU" in first


def test_tests_table_has_the_fourteen_frozen_comparisons() -> None:
    rows, conditions = _rows()
    table = render_tests_table(run_tests(rows, conditions))
    data_rows = [ln for ln in table.splitlines() if ln.startswith("| H") and "Contrast" not in ln]
    assert len(data_rows) == 14  # the 14 frozen comparisons
    assert "p (Holm)" in table


def test_reliability_and_cost_tables_render() -> None:
    rows, conditions = _rows()
    assert "CLS agree" in reliability_table(rows, conditions)
    assert "mean EUR" in cost_table(rows)


def test_write_outputs_md_lists_outputs_with_hypotheses(tmp_path: Path) -> None:
    path = tmp_path / "outputs.md"
    write_outputs_md(["overall_metrics.md", "cost.md"], ["detection_f1.png"], path)
    text = path.read_text(encoding="utf-8")
    assert "overall_metrics.md" in text and "H1" in text
    assert "detection_f1.png" in text
    assert "Tables" in text and "Figures" in text
