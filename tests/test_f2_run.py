"""Real-testbed test for attack family F2, MQTT credential guessing (E1-09). Marked slow."""

from __future__ import annotations

import pytest

from tests.family_run_helpers import (
    count_broker_refused,
    count_flows_for_ip,
    count_honeypot_events,
    device_ip,
    run_family_episode,
    within_tolerance,
)
from thesis.scenario.families.f2 import load_guesses

FAMILY = "mqtt_brute_force"
DEVICE = "iot-temp-01"


@pytest.mark.slow
def test_f2_leaves_refused_auth_and_flow_traces_and_repeats() -> None:
    a = run_family_episode(FAMILY, DEVICE, duration_s=40, seed=1)
    b = run_family_episode(FAMILY, DEVICE, duration_s=40, seed=1)
    ip = device_ip(DEVICE)
    client = f"{DEVICE}-brute"

    mqtt_a = count_broker_refused(a, client)
    mqtt_b = count_broker_refused(b, client)
    flows_a = count_flows_for_ip(a, ip)
    flows_b = count_flows_for_ip(b, ip)

    # Predicted visibility: mqtt yes (refused auth), flows yes, honeypot no.
    assert mqtt_a >= len(load_guesses()) - 2  # one refused CONNECT per guess
    assert flows_a > 0
    assert count_honeypot_events(a) == 0
    assert within_tolerance(FAMILY, "mqtt", mqtt_a, mqtt_b), (mqtt_a, mqtt_b)
    assert within_tolerance(FAMILY, "flows", flows_a, flows_b), (flows_a, flows_b)
