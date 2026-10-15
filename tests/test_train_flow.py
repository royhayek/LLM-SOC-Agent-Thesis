"""Tests for the flow-classifier trainer (E4-02, SCRUM-29)."""

from __future__ import annotations

import random

import numpy as np
import pytest

from thesis.detect import train_flow as tf


def test_macro_f1_perfect_and_partial() -> None:
    y = np.array([0, 0, 1, 1, 2])
    assert tf._macro_f1(y, y.copy(), 3) == 1.0
    wrong = np.array([0, 0, 1, 2, 2])  # one class-1 sample misread as 2
    assert 0.0 < tf._macro_f1(y, wrong, 3) < 1.0


def test_grouped_folds_keep_each_group_whole() -> None:
    groups = [g for g in ("ep-a", "ep-b", "ep-c", "ep-d", "bn-d1") for _ in range(3)]
    folds = tf._grouped_folds(groups, 3, random.Random(1))
    assert sum(len(f) for f in folds) == len(groups)
    # No group appears in more than one fold.
    group_fold: dict[str, int] = {}
    for k, idxs in enumerate(folds):
        for i in idxs:
            g = groups[i]
            assert group_fold.setdefault(g, k) == k


def test_sample_weights_are_inverse_frequency() -> None:
    y = np.array([0, 0, 0, 1])  # class 0 three times, class 1 once
    w = tf._sample_weights(y, 2)
    assert w[3] > w[0]  # the rare class gets more weight
    assert np.isclose(np.sum(w), len(y), atol=1e-6)  # weights sum to n


@pytest.mark.skipif(not tf.TRAIN_TABLE.exists(), reason="training table not on disk")
def test_training_is_deterministic() -> None:
    a = tf.train()
    b = tf.train()
    assert a["best_params"] == b["best_params"]
    assert a["cv_macro_f1"] == b["cv_macro_f1"]
    assert tf.MODEL_PATH.is_file() and tf.META_PATH.is_file()
