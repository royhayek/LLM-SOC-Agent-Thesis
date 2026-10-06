"""Attack family F3: port scan (E1-10; ADR-0003).

An external attacker host runs a TCP connect scan (`nmap -sT`) against the honeypot over a
fixed port set and timing template. A connect scan completes the TCP handshake, so Cowrie
records a session on port 22 (a SYN-only scan would not, and the honeypot cell would be wrong;
ADR-0003). The scan runs in the `attacker` container and addresses the honeypot by IP.
Expected sources: flows and honeypot.

Bounded by the port set, so it finishes within the episode and exits 0.
"""

from __future__ import annotations

from typing import Final

from thesis.scenario.families.base import ATTACKER_SERVICE, SERVICE_IP, ContainerAttackRunner
from thesis.scenario.schedule import AttackFamily, Episode

TARGET: Final = "honeypot"
PORTS: Final = "22,23,80,443,1883,2323,8080,8883,9001"  # fixed port set, honeypot's 22 included
TIMING: Final = "4"  # nmap -T4 timing template, fixed


class PortScanRunner(ContainerAttackRunner):
    family = AttackFamily.PORT_SCAN

    def service_for(self, episode: Episode) -> str:
        return ATTACKER_SERVICE

    def command(self, episode: Episode) -> str:
        ports = str(episode.parameters.get("ports", PORTS))
        timing = str(episode.parameters.get("timing", TIMING))
        target_ip = SERVICE_IP[TARGET]
        # -sT connect scan (completes the handshake), fixed ports, fixed timing, no DNS (-n).
        return f"nmap -sT -n -T{timing} -p {ports} {target_ip}"
