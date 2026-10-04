"""The device-mapping rule, defined once (record §4.1).

D is the non-infrastructure endpoint. Honeypot events key to the honeypot. Cases §4.1
does not cover are ASSUMPTIONs in METHODS.md, "Alert schema v0.1: device mapping (draft)".

The IDs and IPs below are placeholders until the testbed exists. The device inventory
(E5-01, `knowledge/devices.yaml`) replaces them; role and criticality live there, not here.
"""

from __future__ import annotations

from types import MappingProxyType

from thesis.schema.alert import Source

HONEYPOT_ID = "hp-ssh-01"

# Hosts that are never the subject of an incident. Missing one here keys traffic to
# infrastructure and sends bundles to the wrong device.
INFRASTRUCTURE = MappingProxyType(
    {
        "172.20.0.1": "gateway",
        "172.20.0.2": "mqtt-broker",
        "172.20.0.3": "capture-sidecar",
    }
)

# Testbed endpoints that can be the subject of an incident, by IP.
DEVICES = MappingProxyType(
    {
        "172.20.0.10": HONEYPOT_ID,
        "172.20.0.21": "iot-temp-01",
        "172.20.0.22": "iot-cam-01",
    }
)


class AmbiguousSubjectError(ValueError):
    """Both endpoints are testbed devices; §4.1 does not say which one is D."""


def subject_device(source: Source, src_ip: str, dst_ip: str | None) -> str | None:
    """Return the ID of the device an alert is about, or None if no testbed device is involved.

    None covers infrastructure-to-infrastructure traffic and traffic with no known device.
    """
    if source is Source.HONEYPOT:
        return HONEYPOT_ID
    candidates = {DEVICES[ip] for ip in (src_ip, dst_ip) if ip is not None and ip in DEVICES}
    if len(candidates) > 1:
        raise AmbiguousSubjectError(f"{src_ip} -> {dst_ip}: both endpoints are devices")
    return candidates.pop() if candidates else None
