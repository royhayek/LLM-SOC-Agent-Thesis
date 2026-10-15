"""Evaluate and freeze the flow classifier as Baseline A (E4-03, SCRUM-37).

Baseline A must be frozen, hashed and tagged before any agent output exists, so it cannot be
retuned after seeing how the agent does (record §5). The model is evaluated once on **held-out
episodes within the training data** (never the evaluation split, E2-01): a held-out fold of
training episodes is set aside, a model with the frozen best parameters is fit on the rest, and
per-class precision/recall/F1 and macro-F1 are reported on the held-out fold. The committed,
frozen artifact is `models/flow_classifier.txt` (trained on all training data, E4-02); this ticket
records its SHA-256.

    python -m thesis.detect.eval_flow
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import cast

import lightgbm as lgb
import numpy as np

from thesis.detect.train_flow import (
    META_PATH,
    MODEL_PATH,
    N_FOLDS,
    SEED,
    _grouped_folds,
    _load,
    _macro_f1,
    _params,
    _sample_weights,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DOC = REPO_ROOT / "docs" / "detectors" / "flow_eval.md"


def _per_class(
    y_true: np.ndarray, y_pred: np.ndarray, classes: list[str]
) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for c, name in enumerate(classes):
        tp = int(np.sum((y_pred == c) & (y_true == c)))
        fp = int(np.sum((y_pred == c) & (y_true != c)))
        fn = int(np.sum((y_pred != c) & (y_true == c)))
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out[name] = {
            "precision": round(prec, 3),
            "recall": round(rec, 3),
            "f1": round(f1, 3),
            "support": int(np.sum(y_true == c)),
        }
    return out


def evaluate() -> dict[str, object]:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    classes: list[str] = meta["classes"]
    best_params = meta["best_params"]
    class_index = {c: i for i, c in enumerate(classes)}

    x, labels, groups = _load()
    y = np.asarray([class_index[c] for c in labels])
    folds = _grouped_folds(groups, N_FOLDS, random.Random(SEED))
    held_out = max(folds, key=len)  # the largest grouped fold is the held-out test
    train_idx = np.asarray([i for f in folds if f is not held_out for i in f])
    test_idx = np.asarray(held_out)

    dtrain = lgb.Dataset(
        x[train_idx], label=y[train_idx], weight=_sample_weights(y[train_idx], len(classes))
    )
    booster = lgb.train(
        _params(best_params, len(classes)),
        dtrain,
        num_boost_round=cast(int, best_params["num_boost_round"]),
    )
    pred = np.argmax(booster.predict(x[test_idx]), axis=1)

    per_class = _per_class(y[test_idx], pred, classes)
    macro_f1 = round(_macro_f1(y[test_idx], pred, len(classes)), 4)
    sha256 = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
    return {
        "per_class": per_class,
        "macro_f1": macro_f1,
        "sha256": sha256,
        "held_out_flows": int(len(test_idx)),
        "classes": classes,
    }


def freeze(result: dict[str, object]) -> None:
    # Record the frozen model's hash in its metadata file.
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    meta["sha256"] = result["sha256"]
    meta["held_out_macro_f1"] = result["macro_f1"]
    META_PATH.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    per_class = cast(dict[str, dict[str, float]], result["per_class"])
    lines = [
        "# Baseline A (flow classifier) evaluation (E4-03, SCRUM-37)",
        "",
        "Evaluated once on held-out **training** episodes (never the evaluation split, E2-01): a",
        f"held-out grouped fold of {result['held_out_flows']} flows, with a model fit on the",
        "remaining training episodes using the frozen best parameters (E4-02).",
        "",
        f"**Macro-F1 (held-out training episodes): {result['macro_f1']}**",
        "",
        "| Class | Precision | Recall | F1 | Support |",
        "|---|---|---|---|---|",
    ]
    for name, m in per_class.items():
        lines.append(
            f"| {name} | {m['precision']} | {m['recall']} | {m['f1']} | {int(m['support'])} |"
        )
    lines += [
        "",
        f"The frozen model is `models/flow_classifier.txt`, SHA-256 `{result['sha256']}` "
        "(also in `models/flow_classifier.json`). Frozen at git tag `baseline-a-v1.0` before any",
        "agent output exists; any later change needs a changelog entry and a full rerun.",
        "",
    ]
    EVAL_DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    result = evaluate()
    freeze(result)
    print(f"held-out macro-F1 {result['macro_f1']}  sha256 {str(result['sha256'])[:12]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
