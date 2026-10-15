"""The device-mapping rule and inventory, defined once (record §4.1, §6.3).

D is the non-infrastructure endpoint. Honeypot events key to the honeypot. The devices, their IPs,
roles and criticality come from the inventory `knowledge/devices.yaml` (E5-01). Cases §4.1 does not
cover are decided in METHODS.md "Device mapping: cases 4 and 5 (E3-10)": they form no bundle.
"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import yaml  # type: ignore[import-untyped]

from thesis.schema.alert import Source

_INVENTORY = Path(__file__).resolve().parents[2] / "knowledge" / "devices.yaml"


def _load() -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    data = yaml.safe_load(_INVENTORY.read_text(encoding="utf-8"))
    devices = {d["ip"]: d["id"] for d in data["devices"]}
    infra = {h["ip"]: h["id"] for h in data.get("infrastructure", [])}
    criticality = {d["id"]: d["criticality"] for d in data["devices"]}
    role = {d["id"]: d["role"] for d in data["devices"]}
    return devices, infra, criticality, role


_devices, _infra, _criticality, _role = _load()

# Testbed endpoints that can be the subject of an incident, by IP.
DEVICES = MappingProxyType(_devices)
# Hosts that are never the subject of an incident.
INFRASTRUCTURE = MappingProxyType(_infra)
DEVICE_CRITICALITY = MappingProxyType(_criticality)
DEVICE_ROLE = MappingProxyType(_role)
HONEYPOT_ID = next(i for i in _devices.values() if i.startswith("hp-"))


def subject_device(source: Source, src_ip: str, dst_ip: str | None) -> str | None:
    """Return the ID of the device an alert is about, or None if the alert forms no bundle.

    None covers infrastructure-only, external-to-infrastructure (case 4) and device-to-device
    (case 5) traffic (METHODS.md "Device mapping: cases 4 and 5"). Honeypot events always key to the
    honeypot (§4.1).
    """
    if source is Source.HONEYPOT:
        return HONEYPOT_ID
    candidates = {DEVICES[ip] for ip in (src_ip, dst_ip) if ip is not None and ip in DEVICES}
    if len(candidates) > 1:  # device-to-device (case 5): no subject, no bundle
        return None
    return candidates.pop() if candidates else None
