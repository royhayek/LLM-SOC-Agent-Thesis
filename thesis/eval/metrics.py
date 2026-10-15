"""Detection and classification metrics (E9-03, SCRUM-63).

Computes the frozen outcome metrics per condition from the result rows (E9-02): detection
precision/recall/F1 (binary, attack positive) and classification accuracy/macro-F1 over the 7
labels, with a per-label breakdown (record §3.2). Bundle level is primary (§4.1).

An invalid or unparsed output (`incident_type` is None) is **always wrong**, never dropped: a false
negative on an attack bundle and a false positive on a benign one (§3.1). Dropping such rows would
make a model that often fails to answer look more accurate (the gotcha). Metrics are on the emitted
verdict `E`.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping

from thesis.schema.verdict import IncidentType

BENIGN = IncidentType.BENIGN.value
LABELS = [t.value for t in IncidentType]


def _by_condition(rows: Iterable[Mapping[str, object]]) -> dict[str, list[Mapping[str, object]]]:
    groups: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row["config_hash"])].append(row)
    return groups


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0


def _pred(row: Mapping[str, object]) -> str | None:
    """The predicted label, or None for an unusable (withheld/unparsed) output."""
    value = row.get("incident_type")
    return None if value is None else str(value)


def _truth(row: Mapping[str, object]) -> str:
    return str(row["ground_truth"])


def compute_detection(rows: Iterable[Mapping[str, object]]) -> dict[str, dict[str, float]]:
    """Per condition: binary detection with attack as the positive class (§3.2)."""
    out: dict[str, dict[str, float]] = {}
    for config_hash, group in _by_condition(rows).items():
        tp = fp = fn = tn = 0
        for row in group:
            truth_attack = _truth(row) != BENIGN
            pred = _pred(row)
            # An unusable output (None) is always wrong: scored as the opposite of the truth.
            pred_attack = (pred != BENIGN) if pred is not None else (not truth_attack)
            if truth_attack:
                tp, fn = (tp + 1, fn) if pred_attack else (tp, fn + 1)
            else:
                fp, tn = (fp + 1, tn) if pred_attack else (fp, tn + 1)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        out[config_hash] = {
            "precision": precision,
            "recall": recall,
            "f1": _f1(precision, recall),
            "tp": float(tp),
            "fp": float(fp),
            "fn": float(fn),
            "tn": float(tn),
        }
    return out


def compute_classification(rows: Iterable[Mapping[str, object]]) -> dict[str, dict[str, object]]:
    """Per condition: accuracy and macro-F1 over the 7 labels, plus per-label F1 (§3.2)."""
    out: dict[str, dict[str, object]] = {}
    for config_hash, group in _by_condition(rows).items():
        pairs = [(_pred(r), _truth(r)) for r in group]  # (predicted, true); predicted None = wrong
        correct = sum(1 for pred, truth in pairs if pred == truth)
        per_label: dict[str, float] = {}
        for label in LABELS:
            tp = sum(1 for pred, truth in pairs if pred == label and truth == label)
            fp = sum(1 for pred, truth in pairs if pred == label and truth != label)
            fn = sum(1 for pred, truth in pairs if truth == label and pred != label)
            denom = 2 * tp + fp + fn
            per_label[label] = (2 * tp / denom) if denom else 0.0
        out[config_hash] = {
            "accuracy": correct / len(pairs) if pairs else 0.0,
            "macro_f1": sum(per_label.values()) / len(LABELS),
            "per_label_f1": per_label,
        }
    return out


__all__ = ["compute_classification", "compute_detection"]
