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


def subject_device(source: Source, src_ip: str, dst_ip: str | None) -> str | None:
    """Return the ID of the device an alert is about, or None if the alert forms no bundle.

    None covers the cases §4.1 does not key to a device (METHODS.md "Device mapping: cases 4 and
    5 (E3-10)"): traffic with no testbed device, external-to-infrastructure traffic (case 4), and
    device-to-device traffic (case 5). The normalizer skips a None-subject alert with a counted
    reason. Honeypot events always key to the honeypot (§4.1).
    """
    if source is Source.HONEYPOT:
        return HONEYPOT_ID
    candidates = {DEVICES[ip] for ip in (src_ip, dst_ip) if ip is not None and ip in DEVICES}
    # Case 5 (device to device): no frozen family produces lateral movement, so rather than pick
    # one device (arbitrary, risks mislabelling) or key to both (breaks disjoint bundles), the
    # alert forms no bundle. Unexpected such traffic stays visible as a counted skip reason.
    if len(candidates) > 1:
        return None
    return candidates.pop() if candidates else None
