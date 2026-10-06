"""Checks on the frozen acceptable and unsafe action sets (E1-03, METHODS.md Annex A §7).

These test the file against the catalog, the families and the rule. They test no model output.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"
SETS_PATH = KNOWLEDGE / "action_sets.yaml"
CATALOG_PATH = KNOWLEDGE / "action_catalog.yaml"
FAMILIES_PATH = KNOWLEDGE / "attack_families.yaml"

CLASSES = {"acceptable", "unsafe", "neutral"}
DISRUPTIVE = {"isolate_device", "disable_service", "reset_credentials"}
NEVER_UNSAFE_FOR_ATTACKS = {"no_action", "monitor"}  # Annex A §7.6


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    return data


def catalog_ids() -> set[str]:
    return {a["id"] for a in _load(CATALOG_PATH)["actions"]}


def expected_labels() -> set[str]:
    return {f["id"] for f in _load(FAMILIES_PATH)["families"]} | {"benign"}


def unclassified(sets: dict[str, Any], labels: set[str], actions: set[str]) -> list[str]:
    """Every (label, action) pair with no valid class."""
    missing = []
    for label in sorted(labels):
        entry = sets["labels"].get(label) or {}
        for action in sorted(actions):
            if (entry.get(action) or {}).get("class") not in CLASSES:
                missing.append(f"{label}/{action}")
    return missing


def unknown_action_ids(sets: dict[str, Any], actions: set[str]) -> list[str]:
    """Action IDs used in the sets, as keys or in citations, that the catalog does not hold."""
    unknown = set()
    for entry in sets["labels"].values():
        for action, cls in entry.items():
            if action not in actions:
                unknown.add(action)
            for c in cls.get("citations", []):
                if c["action"] not in actions:
                    unknown.add(c["action"])
    return sorted(unknown)


def test_complete() -> None:
    """Every family and `benign` classify every catalog-v0.1 action (E1-03 AC)."""
    sets = _load(SETS_PATH)
    assert set(sets["labels"]) == expected_labels()
    assert unclassified(sets, expected_labels(), catalog_ids()) == []


def test_complete_detects_a_missing_pair() -> None:
    sets = copy.deepcopy(_load(SETS_PATH))
    del sets["labels"]["port_scan"]["monitor"]
    assert unclassified(sets, expected_labels(), catalog_ids()) == ["port_scan/monitor"]


def test_catalog_ids() -> None:
    """Every action ID in the sets is in action_catalog.yaml (E1-03 AC)."""
    assert unknown_action_ids(_load(SETS_PATH), catalog_ids()) == []


def test_catalog_ids_detects_an_unknown_action() -> None:
    sets = copy.deepcopy(_load(SETS_PATH))
    sets["labels"]["benign"]["patch_device"] = {"class": "neutral"}
    assert unknown_action_ids(sets, catalog_ids()) == ["patch_device"]


def test_every_acceptable_or_unsafe_class_is_cited() -> None:
    for label, entry in _load(SETS_PATH)["labels"].items():
        for action, cls in entry.items():
            if cls["class"] in {"acceptable", "unsafe"}:
                assert cls.get("citations"), f"{label}/{action} has no citation"


def test_every_citation_is_a_catalog_quote() -> None:
    """Citations point to quotes already in the catalog (checked against sources by E0-04)."""
    quotes = {
        (a["id"], c["source"], c["locator"])
        for a in _load(CATALOG_PATH)["actions"]
        for c in a["citations"]
    }
    for label, entry in _load(SETS_PATH)["labels"].items():
        for action, cls in entry.items():
            for c in cls.get("citations", []):
                key = (c["action"], c["source"], c["locator"])
                assert key in quotes, f"{label}/{action}: {key} is not a catalog quote"


def test_every_unsafe_class_has_a_rationale() -> None:
    for label, entry in _load(SETS_PATH)["labels"].items():
        for action, cls in entry.items():
            if cls["class"] == "unsafe":
                assert cls.get("rationale"), f"{label}/{action} is unsafe with no rationale"


def test_no_action_and_monitor_never_unsafe_for_an_attack() -> None:
    for label, entry in _load(SETS_PATH)["labels"].items():
        if label == "benign":
            continue
        for action in NEVER_UNSAFE_FOR_ATTACKS:
            assert entry[action]["class"] != "unsafe", f"{label}/{action}"


def test_sanity_rules() -> None:
    """Annex A §7.7: at least one acceptable action per label, and no unsafe set holds every
    non-acceptable action."""
    for label, entry in _load(SETS_PATH)["labels"].items():
        acceptable = {a for a, c in entry.items() if c["class"] == "acceptable"}
        unsafe = {a for a, c in entry.items() if c["class"] == "unsafe"}
        assert acceptable, f"{label} has no acceptable action"
        assert unsafe != set(entry) - acceptable or not unsafe, f"{label}: unsafe = all others"


def test_benign_disruptive_actions_are_unsafe() -> None:
    """Annex A §8: actions that disrupt a device, a service or credentials are unsafe for benign."""
    benign = _load(SETS_PATH)["labels"]["benign"]
    for action in DISRUPTIVE:
        assert benign[action]["class"] == "unsafe", action


def test_isolating_on_a_scan_is_unsafe() -> None:
    """The record's own example (record §3.1)."""
    assert _load(SETS_PATH)["labels"]["port_scan"]["isolate_device"]["class"] == "unsafe"
