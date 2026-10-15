"""Tune the flow classifier (LightGBM) with class-imbalance handling (E4-02, SCRUM-29).

A weak baseline invalidates H4 first (record §6.6), so the flow classifier — which doubles as
Baseline A (§5) — gets a real hyperparameter search with episode-grouped cross-validation and
inverse-frequency sample weights for class imbalance. Folds are grouped by episode so one episode
never spans training and validation (§4.1). Deterministic: the committed seed gives the same best
parameters on every run.

    python -m thesis.detect.train_flow    # writes models/flow_classifier.{txt,json}
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import cast

import lightgbm as lgb
import numpy as np
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from thesis.detect.flow_features import FEATURES

REPO_ROOT = Path(__file__).resolve().parents[2]
TRAIN_TABLE = REPO_ROOT / "data" / "features" / "flows_train.parquet"
MODEL_PATH = REPO_ROOT / "models" / "flow_classifier.txt"
META_PATH = REPO_ROOT / "models" / "flow_classifier.json"
SEARCH_DOC = REPO_ROOT / "docs" / "detectors" / "flow_search.md"

SEED = 20261015
N_TRIALS = 15
N_FOLDS = 3
SEARCH_SPACE: dict[str, list[object]] = {
    "num_leaves": [15, 31, 63],
    "learning_rate": [0.05, 0.1],
    "min_child_samples": [5, 10, 20],
    "num_boost_round": [100, 200],
    "feature_fraction": [0.8, 1.0],
}


def _load() -> tuple[np.ndarray, list[str], list[str]]:
    table = pq.read_table(TRAIN_TABLE)
    feats = list(FEATURES)
    x = np.column_stack([np.asarray(table.column(f).to_pylist(), dtype=float) for f in feats])
    labels = [str(v) for v in table.column("label").to_pylist()]
    episodes = [str(v) for v in table.column("episode_id").to_pylist()]
    devices = [str(v) for v in table.column("device").to_pylist()]
    # Benign flows carry no episode; group them per device so they spread across folds, while every
    # attack episode stays whole in one fold.
    groups = [e if e else f"bn-{d}" for e, d in zip(episodes, devices, strict=True)]
    return x, labels, groups


def _grouped_folds(groups: list[str], n_folds: int, rng: random.Random) -> list[list[int]]:
    unique = sorted(set(groups))
    rng.shuffle(unique)
    fold_of = {g: i % n_folds for i, g in enumerate(unique)}
    folds: list[list[int]] = [[] for _ in range(n_folds)]
    for idx, g in enumerate(groups):
        folds[fold_of[g]].append(idx)
    return folds


def _sample_weights(y: np.ndarray, n_classes: int) -> np.ndarray:
    counts = np.bincount(y, minlength=n_classes)
    inv = {c: len(y) / (n_classes * counts[c]) for c in range(n_classes) if counts[c]}
    return np.asarray([inv[c] for c in y], dtype=float)


def _macro_f1(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> float:
    f1s = []
    for c in range(n_classes):
        tp = int(np.sum((y_pred == c) & (y_true == c)))
        fp = int(np.sum((y_pred == c) & (y_true != c)))
        fn = int(np.sum((y_pred != c) & (y_true == c)))
        if tp + fp + fn == 0:
            continue  # class absent from this evaluation
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return float(np.mean(f1s)) if f1s else 0.0


def _params(trial: dict[str, object], n_classes: int) -> dict[str, object]:
    return {
        "objective": "multiclass",
        "num_class": n_classes,
        "verbosity": -1,
        "seed": SEED,
        "deterministic": True,
        "num_threads": 1,
        "num_leaves": trial["num_leaves"],
        "learning_rate": trial["learning_rate"],
        "min_child_samples": trial["min_child_samples"],
        "feature_fraction": trial["feature_fraction"],
    }


def _cv_macro_f1(
    x: np.ndarray, y: np.ndarray, trial: dict[str, object], n_classes: int, folds: list[list[int]]
) -> float:
    scores = []
    for k, val_idx in enumerate(folds):
        train_idx = [i for j, f in enumerate(folds) if j != k for i in f]
        if not train_idx or not val_idx:
            continue
        tr, va = np.asarray(train_idx), np.asarray(val_idx)
        dtrain = lgb.Dataset(x[tr], label=y[tr], weight=_sample_weights(y[tr], n_classes))
        booster = lgb.train(
            _params(trial, n_classes), dtrain, num_boost_round=cast(int, trial["num_boost_round"])
        )
        pred = np.argmax(booster.predict(x[va]), axis=1)
        scores.append(_macro_f1(y[va], pred, n_classes))
    return float(np.mean(scores)) if scores else 0.0


def train() -> dict[str, object]:
    x, labels, groups = _load()
    classes = sorted(set(labels))
    class_index = {c: i for i, c in enumerate(classes)}
    y = np.asarray([class_index[c] for c in labels])
    n_classes = len(classes)

    rng = random.Random(SEED)
    folds = _grouped_folds(groups, N_FOLDS, rng)
    trials: list[dict[str, object]] = [
        {k: rng.choice(v) for k, v in SEARCH_SPACE.items()} for _ in range(N_TRIALS)
    ]

    results = [(t, _cv_macro_f1(x, y, t, n_classes, folds)) for t in trials]
    best_trial, best_score = max(results, key=lambda r: r[1])

    # Fit the final model on all training data with the best parameters.
    dall = lgb.Dataset(x, label=y, weight=_sample_weights(y, n_classes))
    booster = lgb.train(
        _params(best_trial, n_classes),
        dall,
        num_boost_round=cast(int, best_trial["num_boost_round"]),
    )
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(MODEL_PATH))

    meta = {
        "library": "lightgbm",
        "library_version": lgb.__version__,
        "seed": SEED,
        "classes": classes,
        "features": list(FEATURES),
        "imbalance": "inverse-frequency sample weights",
        "cv": {"folds": N_FOLDS, "grouped_by": "episode", "trials": N_TRIALS},
        "best_params": best_trial,
        "cv_macro_f1": round(best_score, 4),
        "n_training_flows": int(x.shape[0]),
    }
    META_PATH.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta


def _write_doc(meta: dict[str, object]) -> None:
    lines = [
        "# Flow classifier search (E4-02, SCRUM-29)",
        "",
        f"**Library:** {meta['library']} {meta['library_version']} — the record fixes LightGBM or",
        "XGBoost for flows (§6.2); LightGBM is light on 16 GB and fast on this small table. The",
        "classifier doubles as Baseline A (§5), so it is tuned properly (§6.6).",
        "",
        f"- **Search space:** {json.dumps(SEARCH_SPACE)}",
        f"- **Trials:** {meta['cv']['trials']} random draws (seed {meta['seed']}).",  # type: ignore[index]
        f"- **Cross-validation:** {meta['cv']['folds']}-fold, **grouped by episode** so no episode "  # type: ignore[index]
        "spans train and validation folds (§4.1).",
        f"- **Class imbalance:** {meta['imbalance']}.",
        f"- **Best parameters:** {json.dumps(meta['best_params'])}",
        f"- **Cross-validated macro-F1 of the best model:** {meta['cv_macro_f1']}",
        f"- **Training flows:** {meta['n_training_flows']} (training split only, E2-01).",
        "",
        "The model is saved to `models/flow_classifier.txt` with its parameters in",
        "`models/flow_classifier.json`. It is evaluated and frozen as Baseline A in E4-03.",
        "",
    ]
    SEARCH_DOC.parent.mkdir(parents=True, exist_ok=True)
    SEARCH_DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    meta = train()
    _write_doc(meta)
    print(f"best params {meta['best_params']}  cv_macro_f1={meta['cv_macro_f1']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
