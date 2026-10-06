"""Real-testbed test for attack family F6, TCP SYN flood (E1-13). Marked slow."""

from __future__ import annotations

import pytest

from tests.family_run_helpers import (
    count_flows_for_ip,
    count_honeypot_events,
    count_mqtt_topic,
    count_packets_to_port,
    run_family_episode,
    within_tolerance,
)
from thesis.scenario.families.base import SERVICE_IP
from thesis.scenario.families.f6 import DEST_PORT

FAMILY = "syn_flood"
DEVICE = "iot-cam-01"


@pytest.mark.slow
def test_f6_floods_the_device_in_flows_only_and_repeats() -> None:
    a = run_family_episode(FAMILY, DEVICE, duration_s=20, seed=1)
    b = run_family_episode(FAMILY, DEVICE, duration_s=20, seed=1)
    dev_ip = SERVICE_IP["emulator-cam"]

    flows_a = count_flows_for_ip(a, dev_ip)
    flows_b = count_flows_for_ip(b, dev_ip)
    pkts_a = count_packets_to_port(a, dev_ip, DEST_PORT)
    pkts_b = count_packets_to_port(b, dev_ip, DEST_PORT)

    # Predicted visibility: flows only. The one-source family.
    assert pkts_a > 1000  # a flood, not a trickle
    assert count_honeypot_events(a) == 0  # not the honeypot
    assert count_mqtt_topic(a, "/flood") == 0  # no MQTT attack traffic
    assert within_tolerance(FAMILY, "flows", flows_a, flows_b), (flows_a, flows_b)
    assert within_tolerance(FAMILY, "packets", pkts_a, pkts_b), (pkts_a, pkts_b)
