"""Reference tests for the paired hypothesis tests (E9-05, SCRUM-84)."""

from __future__ import annotations

import pytest

from thesis.config import Provenance
from thesis.eval.run import load_conditions
from thesis.eval.stats import COMPARISONS, holm, mcnemar, run_tests, wilcoxon


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


def test_mcnemar_matches_reference_to_four_decimals() -> None:
    # 10 bundles where A is wrong and B right (b01=10); 2 the other way (b10=2).
    a = [False] * 10 + [True] * 2
    b = [True] * 10 + [False] * 2
    stat, p = mcnemar(a, b)
    assert stat == pytest.approx(49 / 12, abs=1e-4)  # (|10-2|-1)^2 / 12
    assert p == pytest.approx(0.0386, abs=1e-4)  # exact two-sided binomial, discordant < 25


def test_mcnemar_no_discordant_pairs_is_p_one() -> None:
    assert mcnemar([True, False], [True, False]) == (0.0, 1.0)


def test_wilcoxon_paired() -> None:
    stat, p = wilcoxon([1.0, 1.0, 1.0, 1.0], [0.0, 0.0, 0.0, 0.0])
    assert stat == pytest.approx(0.0)  # all differences one direction -> zero negative-rank sum
    assert p == pytest.approx(0.125)  # exact minimum for 4 concordant pairs
    assert wilcoxon([1.0, 1.0], [1.0, 1.0]) == (0.0, 1.0)  # no differences -> p = 1


def test_holm_step_down() -> None:
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_comparison_list_matches_methods_exactly() -> None:
    by_h = {h: [c for c in COMPARISONS if c.hypothesis == h] for h in ("H1", "H2", "H3", "H4")}
    assert len(by_h["H1"]) == 6  # C1 vs C2/C3/C4 on DET, CLS
    assert len(by_h["H2"]) == 1  # C5 vs C6 on CLS
    assert len(by_h["H3"]) == 1  # C1 vs C5 on CU (Wilcoxon)
    assert len(by_h["H4"]) == 6  # C1 vs C7/C6 on DET, CLS, CU
    assert len(COMPARISONS) == 14
    assert by_h["H3"][0].test == "wilcoxon"
    assert all(c.test == "wilcoxon" for c in by_h["H4"] if c.outcome == "CU")


def _row(cfg: str, bundle: str, rep: int, truth: str, pred: str, action: str) -> dict[str, object]:
    return {
        "config_hash": cfg,
        "bundle_id": bundle,
        "repetition": rep,
        "ground_truth": truth,
        "emitted": True,
        "incident_type": pred,
        "recommended_action": action,
        "evidence": [],
        "validator_outcome": "pass",
    }


def test_run_tests_produces_one_row_per_frozen_comparison() -> None:
    from thesis.config import config_hash

    conditions = load_conditions(_prov())
    hashes = [config_hash(c) for c in conditions]
    rows: list[dict[str, object]] = []
    for cfg in hashes:
        for b in ("b1", "b2"):
            for r in range(3):
                rows.append(_row(cfg, b, r, "syn_flood", "syn_flood", "rate_limit_source"))
    results = run_tests(rows, conditions)
    assert len(results) == 14  # exactly the frozen comparisons, no more
    assert {r.hypothesis for r in results} == {"H1", "H2", "H3", "H4"}
    assert all(0.0 <= r.p_holm <= 1.0 for r in results)
