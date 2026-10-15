"""Baseline A: the flow classifier plus the frozen severity->action lookup (E8-02, SCRUM-46).

Baseline A answers "is an LLM needed at all?" (record §6.6). It makes **no LLM call**: it reads the
same reduced view the agent sees (§4.1), takes the flows detector label and score the classifier
already produced (E4-06), turns the score into a severity and the (family, severity) pair into a
catalog action with the frozen lookup (E8-01). The verdict is benign when the view has no flows
block (E0-05). It carries no evidence — Baseline A cannot cite alerts — so `evidence` is empty, and
E0-12 fixes how that is scored (never invent evidence).

The frozen model's SHA-256 is checked at load (tag `baseline-a-v1.0`, E4-03): a mismatch aborts the
run, so Baseline A can only run against the exact frozen classifier.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import cast

import yaml  # type: ignore[import-untyped]

from thesis.schema.verdict import Severity, Verdict

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = REPO_ROOT / "models" / "flow_classifier.txt"
LOOKUP_PATH = REPO_ROOT / "knowledge" / "baseline_a_lookup.yaml"

# SHA-256 of the frozen flow classifier (E4-03, tag `baseline-a-v1.0`; docs/detectors/flow_eval.md).
FROZEN_MODEL_SHA256 = "1aa54a1636fc4c33874a958a44b42febb8cb05146a24523ed2b72341cb8a235d"


class FrozenModelError(RuntimeError):
    """The flow classifier on disk is not the frozen Baseline A model."""


def verify_model(path: Path = MODEL_PATH, expected: str = FROZEN_MODEL_SHA256) -> None:
    """Abort unless the classifier file matches the frozen Baseline A hash (E4-03)."""
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise FrozenModelError(f"{path} sha256 {actual} != frozen {expected}")


def _load_lookup() -> dict[str, object]:
    return cast("dict[str, object]", yaml.safe_load(LOOKUP_PATH.read_text(encoding="utf-8")))


def _severity(score: float, thresholds: dict[str, float]) -> Severity:
    """The highest severity band whose lower bound is <= the classifier score (the frozen rule)."""
    for name in ("critical", "high", "medium", "low"):
        if score >= float(thresholds[name]):
            return Severity(name)
    return Severity.LOW


def baseline_a_verdict(view: dict[str, object]) -> Verdict:
    """Return Baseline A's verdict for one reduced bundle view. Deterministic; makes no LLM call."""
    verify_model()
    lookup = _load_lookup()
    rule = cast("dict[str, object]", lookup["severity_rule"])
    thresholds = {k: float(v) for k, v in cast("dict[str, float]", rule["thresholds"]).items()}

    flows = view.get("flows")
    label, score = "benign", 0.0
    if isinstance(flows, dict):
        detector = flows.get("detector")
        if isinstance(detector, dict) and detector.get("label"):
            label = str(detector["label"])
            score = float(detector.get("max_score", 0.0))

    severity = _severity(score, thresholds)
    table = cast("dict[str, dict[str, dict[str, str]]]", lookup["lookup"])
    action = table[label][severity.value]["action"]
    return Verdict.model_validate(
        {
            "classification": {"incident_type": label, "confidence": score},
            "recommendation": {"recommended_action": action, "severity": severity.value},
            "affected_device": str(view.get("device", "unknown")),
            "evidence": [],  # Baseline A cites no alerts (§6.6); E0-12 scores the empty field
        }
    )


__all__ = ["FROZEN_MODEL_SHA256", "FrozenModelError", "baseline_a_verdict", "verify_model"]
