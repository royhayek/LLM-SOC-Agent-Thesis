"""Tests for the frozen Baseline A severity->action lookup (E8-01, SCRUM-35)."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]

from thesis.schema.verdict import ACTION_IDS, IncidentType, Severity

ROOT = Path(__file__).resolve().parent.parent
LOOKUP = yaml.safe_load((ROOT / "knowledge" / "baseline_a_lookup.yaml").read_text(encoding="utf-8"))
CATALOG = yaml.safe_load((ROOT / "knowledge" / "action_catalog.yaml").read_text(encoding="utf-8"))
_SOURCES = set(CATALOG["sources"])

LABELS = [t.value for t in IncidentType]
SEVERITIES = [s.value for s in Severity]


def test_every_label_and_severity_pair_is_mapped() -> None:
    table = LOOKUP["lookup"]
    assert set(table) == set(LABELS)  # all six families plus benign
    for label in LABELS:
        assert set(table[label]) == set(SEVERITIES), f"{label} is missing a severity"


def test_every_action_is_in_the_catalog() -> None:
    for label, by_sev in LOOKUP["lookup"].items():
        for severity, entry in by_sev.items():
            assert entry["action"] in ACTION_IDS, (
                f"{label}/{severity}: {entry['action']} not a catalog id"
            )


def test_every_mapping_has_a_citation_from_a_catalog_source() -> None:
    for label, by_sev in LOOKUP["lookup"].items():
        for severity, entry in by_sev.items():
            cite = entry["citation"]
            assert cite["source"] in _SOURCES, (
                f"{label}/{severity}: unknown source {cite['source']}"
            )
            assert cite["locator"].strip(), f"{label}/{severity}: empty locator"


def test_benign_is_no_action_at_every_severity() -> None:
    for severity in SEVERITIES:
        assert LOOKUP["lookup"]["benign"][severity]["action"] == "no_action"


def test_severity_rule_is_stated_with_thresholds() -> None:
    rule = LOOKUP["severity_rule"]
    assert set(rule["thresholds"]) == set(SEVERITIES)
    assert rule["thresholds"]["low"] == 0.0 and rule["thresholds"]["critical"] == 0.9
