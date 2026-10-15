"""Tests for the exploratory-run harness (E9-08, SCRUM-107).

The pure pieces are tested here: the seeded slice, the cost projection, the end-to-end metric run
and the report writer. The live `main()` (real model calls, full assembly) is Roy's run, not a
unit test.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from thesis.config import Provenance, config_hash
from thesis.eval.cost import USD_PER_EUR
from thesis.eval.exploratory import (
    CAP_USD,
    draw_slice,
    project_cost,
    run_all_metrics,
    write_report,
)
from thesis.eval.run import K, load_conditions


@dataclass(frozen=True)
class _FakeBundle:
    bundle_id: str
    label: str


def _bundles() -> list[_FakeBundle]:
    # 60 attack bundles across 3 labels + 30 benign = 90.
    out: list[_FakeBundle] = []
    for label in ("syn_flood", "port_scan", "botnet"):
        out += [_FakeBundle(f"{label}-{i:03d}", label) for i in range(20)]
    out += [_FakeBundle(f"benign-{i:03d}", "benign") for i in range(30)]
    return out


def test_draw_slice_is_seeded_stratified_and_a_subset() -> None:
    bundles = _bundles()
    first = draw_slice(bundles, fraction=0.10, seed=1)
    second = draw_slice(bundles, fraction=0.10, seed=1)
    assert [b.bundle_id for b in first] == [b.bundle_id for b in second]  # deterministic
    assert {b.bundle_id for b in first} <= {b.bundle_id for b in bundles}  # subset
    labels = {b.label for b in first}
    assert labels == {"syn_flood", "port_scan", "botnet", "benign"}  # every label present
    assert len(first) == 2 + 2 + 2 + 3  # round(20*.1)=2 per attack family, round(30*.1)=3 benign
    assert draw_slice(bundles, fraction=0.10, seed=2) != first  # a different seed moves the draw


def test_draw_slice_keeps_at_least_one_per_present_label() -> None:
    bundles = [_FakeBundle("a-0", "syn_flood"), _FakeBundle("b-0", "benign")]
    chosen = draw_slice(bundles, fraction=0.01, seed=1)  # fraction rounds to 0 -> floor of 1
    assert {b.label for b in chosen} == {"syn_flood", "benign"}


def _cost_row(bundle: str, tokens_in: int, tokens_out: int) -> dict[str, object]:
    return {"bundle_id": bundle, "tokens_in": tokens_in, "tokens_out": tokens_out}


def test_project_cost_hand_computed() -> None:
    rows = [_cost_row("b1", 1_000_000, 0), _cost_row("b2", 1_000_000, 0)]  # USD 0.02 each
    cost = project_cost(rows, n_eval=20)  # n_slice = 2, K scaling
    assert cost.measured_usd == pytest.approx(0.04)
    assert cost.measured_eur == pytest.approx(round(0.04 / USD_PER_EUR, 4))
    # scale = (20/2) * K; per full run = 0.04 * 10 * K
    assert cost.per_full_run_usd == pytest.approx(0.04 * 10 * K)
    # total = per_full_run * 3 full runs + the exploratory run itself
    assert cost.projected_total_usd == pytest.approx(0.04 * 10 * K * 3 + 0.04)
    assert cost.within_cap is True  # well under USD 20
    assert cost.n_slice == 2 and cost.n_eval == 20


def test_project_cost_flags_over_cap() -> None:
    rows = [_cost_row("b1", 1_000_000_000, 0)]  # USD 20 on one bundle
    cost = project_cost(rows, n_eval=480, cap_usd=CAP_USD)
    assert cost.within_cap is False


def _prov() -> Provenance:
    return Provenance(
        model="m",
        model_revision="r",
        provider="p",
        temperature=0.6,
        top_p=0.9,
        max_tokens=250,
        seed=None,
        prompt_template_version="prompts-v1.0",
        graph_version="graph-v1.0",
    )


def _metric_row(cfg: str, bundle: str, rep: int) -> dict[str, object]:
    return {
        "config_hash": cfg,
        "bundle_id": bundle,
        "repetition": rep,
        "ground_truth": "syn_flood",
        "episode_id": "ep-syn_flood-eval-001",
        "emitted": True,
        "validator_outcome": "pass",
        "incident_type": "syn_flood",
        "recommended_action": "rate_limit_source",
        "evidence": [],
        "tokens_in": 1000,
        "tokens_out": 100,
        "latency_ms": 1500.0,
    }


def _full_rows() -> tuple[list[dict[str, object]], list]:
    conditions = load_conditions(_prov())
    rows: list[dict[str, object]] = []
    for cond in conditions:
        cfg = config_hash(cond)
        for b in ("b1", "b2"):
            for r in range(K):
                rows.append(_metric_row(cfg, b, r))
    return rows, conditions


def test_run_all_metrics_exercises_every_function() -> None:
    rows, conditions = _full_rows()
    ran = run_all_metrics(rows, conditions)
    assert ran == [
        "detection",
        "classification",
        "safety",
        "reliability",
        "cost_per_incident",
        "hypothesis_tests",
        "block_bootstrap",
    ]


def test_run_all_metrics_raises_naming_the_failing_metric() -> None:
    rows, conditions = _full_rows()
    for row in rows:
        del row["ground_truth"]  # detection reads this first -> KeyError, wrapped with context
    with pytest.raises(RuntimeError, match="detection"):
        run_all_metrics(rows, conditions)


def test_write_report_has_cost_projection_and_human_sections(tmp_path: Path) -> None:
    rows = [_cost_row("b1", 1_000_000, 0), _cost_row("b2", 1_000_000, 0)]
    cost = project_cost(rows, n_eval=20)
    path = tmp_path / "exploratory_run.md"
    write_report(cost, ["detection", "block_bootstrap"], eval_hash="deadbeef", path=path)
    text = path.read_text(encoding="utf-8")
    assert str(cost.measured_eur) in text  # actual euros spent
    assert str(cost.projected_total_eur) in text  # projected euros for the full runs
    assert "deadbeef" in text  # eval-set hash for traceability
    assert "WITHIN CAP" in text
    assert "## Bugs found and fixed" in text  # human section
    assert "Parameter-change confirmation" in text  # no-change confirmation
    assert "- detection" in text and "- block_bootstrap" in text  # metrics that ran
