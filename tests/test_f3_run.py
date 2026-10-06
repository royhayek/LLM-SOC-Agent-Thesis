"""Real-testbed test for attack family F3, port scan (E1-10). Marked slow."""

from __future__ import annotations

import pytest

from tests.family_run_helpers import (
    count_flows_for_ip,
    count_honeypot_events,
    run_family_episode,
    within_tolerance,
)
from thesis.scenario.families.base import SERVICE_IP

FAMILY = "port_scan"
DEVICE = "hp-ssh-01"  # the honeypot is the subject (attacked)


@pytest.mark.slow
def test_f3_leaves_flow_and_honeypot_traces_and_repeats() -> None:
    a = run_family_episode(FAMILY, DEVICE, duration_s=40, seed=1)
    b = run_family_episode(FAMILY, DEVICE, duration_s=40, seed=1)
    attacker_ip = SERVICE_IP["attacker"]

    flows_a = count_flows_for_ip(a, attacker_ip)
    flows_b = count_flows_for_ip(b, attacker_ip)
    hp_a = count_honeypot_events(a)
    hp_b = count_honeypot_events(b)

    # Predicted visibility: flows yes, honeypot yes, mqtt no.
    assert flows_a > 0
    assert hp_a > 0  # the connect scan completes the handshake on 22, so Cowrie logs it
    assert within_tolerance(FAMILY, "flows", flows_a, flows_b), (flows_a, flows_b)
    assert within_tolerance(FAMILY, "honeypot", hp_a, hp_b), (hp_a, hp_b)
