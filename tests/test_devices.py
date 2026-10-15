"""Tests for the device inventory (E5-01, SCRUM-26)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from thesis.schema.devices import DEVICE_CRITICALITY, DEVICE_ROLE, DEVICES

REPO = Path(__file__).resolve().parent.parent
INVENTORY = yaml.safe_load((REPO / "knowledge" / "devices.yaml").read_text(encoding="utf-8"))
_CRITICALITY = {"low", "medium", "high"}


def _compose_device_ids() -> set[str]:
    """Subject device ids declared in docker-compose.yml (emulator-* services and the honeypot)."""
    text = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    ids = set(re.findall(r"iot-[a-z]+-\d+", text))
    if "honeypot" in text:
        ids.add("hp-ssh-01")
    return ids


def test_every_entry_has_the_required_fields() -> None:
    for d in INVENTORY["devices"]:
        assert set(d) >= {"id", "role", "criticality", "ip", "position"}
        assert d["criticality"] in _CRITICALITY


def test_every_compose_device_is_in_the_inventory() -> None:
    inventory_ids = {d["id"] for d in INVENTORY["devices"]}
    missing = _compose_device_ids() - inventory_ids
    assert not missing, f"devices missing from the inventory: {sorted(missing)}"


def test_inventory_loads_into_the_device_maps() -> None:
    assert set(DEVICE_CRITICALITY) == {d["id"] for d in INVENTORY["devices"]}
    assert all(v in _CRITICALITY for v in DEVICE_CRITICALITY.values())
    assert DEVICE_ROLE["iot-cam-01"] == "ip-camera"
    assert "10.77.0.21" in DEVICES and DEVICES["10.77.0.21"] == "iot-temp-01"
