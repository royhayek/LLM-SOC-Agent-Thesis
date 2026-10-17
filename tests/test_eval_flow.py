"""Tests for Baseline A evaluation (E4-03, SCRUM-37)."""

from __future__ import annotations

import numpy as np
import pytest

from thesis.detect import eval_flow as ev
from thesis.detect.train_flow import META_PATH, TRAIN_TABLE


def test_per_class_metrics() -> None:
    y = np.array([0, 0, 1, 1])
    pred = np.array([0, 0, 1, 0])  # one class-1 sample misread as 0
    pc = ev._per_class(y, pred, ["benign", "attack"])
    assert pc["benign"]["recall"] == 1.0 and pc["benign"]["support"] == 2
    assert pc["attack"]["recall"] == 0.5 and pc["attack"]["precision"] == 1.0


# evaluate() needs both the trained model (META_PATH, committed) and the training feature table
# (TRAIN_TABLE, under the gitignored data/). CI has the model but not the data, so guard on both,
# else the test runs there and fails on the missing parquet instead of skipping.
@pytest.mark.skipif(
    not (META_PATH.exists() and TRAIN_TABLE.exists()),
    reason="trained model or training feature table not on disk",
)
def test_evaluate_reports_hash_and_macro_f1() -> None:
    result = ev.evaluate()
    assert len(result["sha256"]) == 64  # type: ignore[arg-type]
    assert 0.0 <= result["macro_f1"] <= 1.0  # type: ignore[operator]
    assert set(result["per_class"]) <= set(result["classes"])  # type: ignore[arg-type]
