"""Tests for the scenario schedule format and its validator (E1-06, record §4.1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from thesis.scenario.schedule import AttackFamily, Schedule, load_schedule
from thesis.schema.verdict import IncidentType

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_PATH = ROOT / "schedules" / "example.yaml"
FAMILIES_PATH = ROOT / "knowledge" / "attack_families.yaml"


def episode(
    id: str, start: int, duration: int, device: str = "iot-temp-01", family: str = "syn_flood"
) -> dict[str, Any]:
    return {
        "id": id,
        "family": family,
        "target_device": device,
        "start_offset_s": start,
        "duration_s": duration,
        "parameters": {},
        "seed": 0,
    }


def test_overlap_on_same_device_names_both_episodes() -> None:
    with pytest.raises(ValidationError) as exc:
        Schedule.model_validate({"episodes": [episode("ep-a", 0, 120), episode("ep-b", 60, 120)]})
    assert "ep-a" in str(exc.value)
    assert "ep-b" in str(exc.value)


def test_unknown_family_is_named() -> None:
    with pytest.raises(ValidationError) as exc:
        Schedule.model_validate({"episodes": [episode("ep-a", 0, 60, family="ransomware")]})
    assert "ransomware" in str(exc.value)


def test_example_schedule_is_valid_with_one_episode_per_family() -> None:
    schedule = load_schedule(EXAMPLE_PATH)
    assert sorted(e.family for e in schedule.episodes) == sorted(AttackFamily)


@pytest.mark.parametrize("family", [["syn_flood"], {"id": "syn_flood"}])
def test_non_string_family_is_a_validation_error(family: object) -> None:
    with pytest.raises(ValidationError):
        Schedule.model_validate({"episodes": [{**episode("ep-a", 0, 60), "family": family}]})


@pytest.mark.parametrize("field", ["seed", "start_offset_s", "duration_s"])
def test_boolean_is_not_an_integer(field: str) -> None:
    with pytest.raises(ValidationError):
        Schedule.model_validate({"episodes": [{**episode("ep-a", 0, 60), field: True}]})


def test_episodes_touching_end_to_start_are_adjacent() -> None:
    Schedule.model_validate({"episodes": [episode("ep-a", 0, 60), episode("ep-b", 60, 60)]})


def test_overlap_by_one_second_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Schedule.model_validate({"episodes": [episode("ep-a", 0, 61), episode("ep-b", 60, 60)]})


def test_overlap_on_different_devices_is_allowed() -> None:
    Schedule.model_validate(
        {
            "episodes": [
                episode("ep-a", 0, 120, device="iot-temp-01"),
                episode("ep-b", 60, 120, device="iot-cam-01"),
            ]
        }
    )


def test_benign_is_not_an_attack_family() -> None:
    with pytest.raises(ValidationError):
        Schedule.model_validate({"episodes": [episode("ep-a", 0, 60, family="benign")]})


def test_duplicate_ids_are_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        Schedule.model_validate({"episodes": [episode("ep-a", 0, 60), episode("ep-a", 120, 60)]})
    assert "ep-a" in str(exc.value)


def test_attack_family_matches_frozen_families() -> None:
    with FAMILIES_PATH.open(encoding="utf-8") as f:
        frozen = {fam["id"] for fam in yaml.safe_load(f)["families"]}
    assert {f.value for f in AttackFamily} == frozen
    assert {f.value for f in AttackFamily} == {t.value for t in IncidentType} - {"benign"}
