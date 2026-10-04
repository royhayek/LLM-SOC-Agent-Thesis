"""Checks on the frozen action catalog (E0-04). These test the file, not any model output."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CATALOG_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "action_catalog.yaml"


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        catalog: dict[str, Any] = yaml.safe_load(f)
    return catalog


def uncited_actions(catalog: dict[str, Any]) -> list[str]:
    """Return the ids of actions with no citation."""
    return [a.get("id", "<no id>") for a in catalog["actions"] if not a.get("citations")]


def test_every_action_cited() -> None:
    assert uncited_actions(load_catalog()) == []


def test_uncited_action_is_detected() -> None:
    catalog = load_catalog()
    catalog["actions"][0]["citations"] = []
    assert uncited_actions(catalog) == [catalog["actions"][0]["id"]]


def test_catalog_has_6_to_8_actions_with_required_fields() -> None:
    actions = load_catalog()["actions"]
    assert 6 <= len(actions) <= 8
    for action in actions:
        for field in ("id", "name", "description", "citations"):
            assert action.get(field), f"{action.get('id')} is missing {field}"
    ids = [a["id"] for a in actions]
    assert len(ids) == len(set(ids))


def test_every_citation_names_a_listed_source() -> None:
    catalog = load_catalog()
    for action in catalog["actions"]:
        for citation in action["citations"]:
            assert citation["source"] in catalog["sources"], action["id"]
            assert citation["locator"] and citation["quote"], action["id"]


def test_every_description_starts_with_recommend() -> None:
    for action in load_catalog()["actions"]:
        assert action["description"].startswith("Recommend"), action["id"]
