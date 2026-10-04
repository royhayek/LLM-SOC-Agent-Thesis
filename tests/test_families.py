"""Checks on the frozen attack families (E1-02). These test the file, not any model output."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from thesis.schema.alert import Source
from thesis.schema.verdict import IncidentType

FAMILIES_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "attack_families.yaml"
SOURCES = [s.value for s in Source]
REQUIRED_COVERAGE = {"dos", "scanning", "brute_force", "botnet"}


def load_families(path: Path = FAMILIES_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        families: dict[str, Any] = yaml.safe_load(f)
    return families


def source_counts(families: dict[str, Any]) -> dict[str, int]:
    """Return, for each family, the number of sources in which it leaves traces."""
    return {f["id"]: sum(f["visibility"][s] for s in SOURCES) for f in families["families"]}


def stratification_violations(families: dict[str, Any]) -> list[str]:
    """Return the clauses of the stratification rule the visibility matrix breaks."""
    counts = list(source_counts(families).values())
    violations = []
    if any(c == 3 for c in counts):
        violations.append("a family leaves traces in all three sources")
    if sum(c == 2 for c in counts) < 4:
        violations.append("fewer than four families leave traces in exactly two sources")
    if sum(c == 1 for c in counts) < 1:
        violations.append("no family leaves traces in exactly one source")
    for source in ("mqtt", "honeypot"):
        if sum(f["visibility"][source] for f in families["families"]) < 2:
            violations.append(f"{source} sees fewer than two families")
    return violations


def test_stratification() -> None:
    assert stratification_violations(load_families()) == []


def test_stratification_violation_is_detected() -> None:
    families = load_families()
    families["families"][0]["visibility"] = {"mqtt": True, "flows": True, "honeypot": True}
    assert "a family leaves traces in all three sources" in stratification_violations(families)


def test_six_families_with_required_fields() -> None:
    families = load_families()
    entries = families["families"]
    assert len(entries) == 6
    ids = [f["id"] for f in entries]
    assert len(ids) == len(set(ids))
    for family in entries:
        for field in ("id", "name", "covers", "target", "attack", "datasets", "visibility"):
            assert family.get(field), f"{family.get('id')} is missing {field}"
        assert family["attack"]["technique"].startswith("T"), family["id"]
        for dataset in family["datasets"]:
            assert dataset["ref"] in {"[6]", "[7]", "[8]", "[9]"}, family["id"]
            assert dataset["ref"] in families["datasets"], family["id"]


def test_visibility_matrix_is_complete_yes_or_no() -> None:
    for family in load_families()["families"]:
        assert sorted(family["visibility"]) == sorted(SOURCES), family["id"]
        assert all(isinstance(v, bool) for v in family["visibility"].values()), family["id"]


def test_required_attack_types_covered() -> None:
    covered = {f["covers"] for f in load_families()["families"]}
    assert REQUIRED_COVERAGE <= covered


def test_rule_is_one_sentence() -> None:
    rule = load_families()["stratification_rule"].strip()
    assert rule.endswith(".") and rule.count(".") == 1


def test_enum_matches_families_plus_benign() -> None:
    ids = {f["id"] for f in load_families()["families"]}
    assert len(IncidentType) == 7
    assert {t.value for t in IncidentType} == ids | {"benign"}
