"""Hand-computed tests for the detection/classification metrics (E9-03, SCRUM-63)."""

from __future__ import annotations

import pytest

from thesis.eval.metrics import compute_classification, compute_detection


def _row(truth: str, pred: str | None, cfg: str = "c1") -> dict[str, object]:
    return {"config_hash": cfg, "ground_truth": truth, "incident_type": pred}


# 5 rows: tp=1 (syn->syn); fn: botnet->benign, port_scan->None; fp: benign->syn; tn: benign->benign
ROWS = [
    _row("syn_flood", "syn_flood"),
    _row("botnet", "benign"),
    _row("benign", "benign"),
    _row("benign", "syn_flood"),
    _row("port_scan", None),  # unparsed -> counts as wrong (false negative on an attack)
]


def test_detection_matches_hand_counts() -> None:
    det = compute_detection(ROWS)["c1"]
    assert (det["tp"], det["fp"], det["fn"], det["tn"]) == (1.0, 1.0, 2.0, 1.0)
    assert det["precision"] == pytest.approx(0.5)
    assert det["recall"] == pytest.approx(1 / 3)
    assert det["f1"] == pytest.approx(0.4)


def test_classification_matches_hand_counts() -> None:
    cls = compute_classification(ROWS)["c1"]
    assert cls["accuracy"] == pytest.approx(0.4)  # 2 of 5 correct
    per_label = cls["per_label_f1"]
    assert per_label["syn_flood"] == pytest.approx(2 / 3)  # tp1 fp1 fn0
    assert per_label["benign"] == pytest.approx(0.5)  # tp1 fp1 fn1
    assert per_label["botnet"] == pytest.approx(0.0)
    assert cls["macro_f1"] == pytest.approx((2 / 3 + 0.5) / 7)


def test_unparsed_output_counts_as_wrong_not_dropped() -> None:
    # One attack bundle, prediction failed to parse -> recall 0, accuracy 0 (not dropped).
    rows = [_row("syn_flood", None)]
    det = compute_detection(rows)["c1"]
    cls = compute_classification(rows)["c1"]
    assert det["fn"] == 1.0 and det["recall"] == pytest.approx(0.0)
    assert cls["accuracy"] == pytest.approx(0.0)


def test_metrics_are_grouped_per_condition() -> None:
    rows = [_row("syn_flood", "syn_flood", cfg="a"), _row("syn_flood", "benign", cfg="b")]
    det = compute_detection(rows)
    assert set(det) == {"a", "b"}
    assert det["a"]["recall"] == pytest.approx(1.0)
    assert det["b"]["recall"] == pytest.approx(0.0)
