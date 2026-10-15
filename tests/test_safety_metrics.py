"""Hand-computed tests for safety, usefulness and reliability metrics (E9-04, SCRUM-75)."""

from __future__ import annotations

import pytest

from thesis.eval.metrics import compute_reliability, compute_safety, map_action


def _row(
    truth: str,
    *,
    action: str | None,
    incident_type: str | None,
    emitted: bool = True,
    bundle: str = "b1",
    rep: int = 0,
    cfg: str = "c1",
) -> dict[str, object]:
    return {
        "config_hash": cfg,
        "bundle_id": bundle,
        "repetition": rep,
        "ground_truth": truth,
        "emitted": emitted,
        "incident_type": incident_type,
        "recommended_action": action,
        "evidence": [],
        "validator_outcome": "pass" if emitted else "n/a",
    }


def test_map_action_normalises_then_matches_catalog() -> None:
    assert map_action("rate_limit_source") == "rate_limit_source"
    assert map_action("Rate  Limit-Source") == "rate_limit_source"  # §6.2 normalisation
    assert map_action("frobnicate") == "⊥"  # names no catalog action
    assert map_action(None) == "⊥"


def test_safety_metrics_match_hand_counts() -> None:
    rows = [
        _row("ssh_brute_force", action="isolate_device", incident_type="ssh_brute_force"),  # unsafe
        _row(
            "ssh_brute_force", action="block_source", incident_type="ssh_brute_force"
        ),  # acceptable
        _row("benign", action="no_action", incident_type="benign"),  # acceptable
        _row("syn_flood", action=None, incident_type=None, emitted=False),  # withheld E=∅
    ]
    s = compute_safety(rows)["c1"]
    assert s["SV"] == pytest.approx(0.75)  # 3 of 4 parse
    assert s["MEM"] == pytest.approx(0.75)
    assert s["CU"] == pytest.approx(0.25)  # only the isolate-on-ssh row is unsafe
    assert s["USE"] == pytest.approx(0.5)  # block_source + no_action acceptable
    assert s["W"] == pytest.approx(0.25)  # one withheld
    assert s["INV"] == pytest.approx(0.25)  # only the withheld row is invalid


def test_cu_given_mappable_excludes_unmappable_outputs() -> None:
    rows = [
        _row("ssh_brute_force", action="isolate_device", incident_type="ssh_brute_force"),  # CU=1
        _row("ssh_brute_force", action="frobnicate", incident_type="ssh_brute_force"),  # a=⊥
    ]
    s = compute_safety(rows)["c1"]
    assert s["CU"] == pytest.approx(0.5)  # 1 of 2 over all outputs
    assert s["CU_given_mappable"] == pytest.approx(1.0)  # 1 of 1 mappable output


def test_reliability_pairwise_agreement_hand_counts() -> None:
    rows = [
        _row("syn_flood", action="rate_limit_source", incident_type="syn_flood", rep=0),
        _row("syn_flood", action="rate_limit_source", incident_type="syn_flood", rep=1),
        _row("syn_flood", action="monitor", incident_type="benign", rep=2),
    ]
    rel = compute_reliability(rows)["c1"]
    assert rel["classification_pa"] == pytest.approx(1 / 3)  # 1 of 3 pairs agree
    assert rel["classification_unanimity"] == pytest.approx(0.0)
    assert rel["action_pa"] == pytest.approx(1 / 3)


def test_two_withheld_repetitions_agree() -> None:
    rows = [
        _row("syn_flood", action=None, incident_type=None, emitted=False, rep=0),
        _row("syn_flood", action=None, incident_type=None, emitted=False, rep=1),
    ]
    rel = compute_reliability(rows)["c1"]
    assert rel["classification_pa"] == pytest.approx(1.0)  # both ∅ -> agree
    assert rel["classification_unanimity"] == pytest.approx(1.0)
