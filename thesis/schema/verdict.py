"""Verdict schema (record §6.5). For now only the label space: `incident_type`.

The six attack families are frozen in `knowledge/attack_families.yaml` (E1-02, tag
`families-v1.0`). A test checks that this enum and that file name the same families.
"""

from __future__ import annotations

from enum import StrEnum


class IncidentType(StrEnum):
    """The six attack families plus `benign` (record §6.5, METHODS.md Changelog entry 1)."""

    SSH_BRUTE_FORCE = "ssh_brute_force"
    PORT_SCAN = "port_scan"
    MQTT_PUBLISH_FLOOD = "mqtt_publish_flood"
    MQTT_BRUTE_FORCE = "mqtt_brute_force"
    SYN_FLOOD = "syn_flood"
    BOTNET = "botnet"
    BENIGN = "benign"
