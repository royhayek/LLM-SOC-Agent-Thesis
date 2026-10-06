"""Attack family F4: SSH credential guessing (E1-11; ADR-0003).

An external attacker host guesses SSH logins against the honeypot with THC-Hydra, over a fixed
username list and password list committed under `scenarios/`. Hydra completes the TCP (and SSH)
handshake, so Cowrie logs the attempts. The attack runs in the `attacker` container and
addresses the honeypot by IP. Expected sources: flows and honeypot.

Every username x password pair is tried once (no early exit), at a fixed task count, so the
attempt count is fixed and the attack finishes within the episode and exits 0. This is the
same scenario as the walking-skeleton spike (record §9).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from thesis.scenario.families.base import ATTACKER_SERVICE, SERVICE_IP, ContainerAttackRunner
from thesis.scenario.schedule import AttackFamily, Episode

REPO_ROOT: Final = Path(__file__).resolve().parent.parent.parent.parent
SCENARIOS: Final = REPO_ROOT / "scenarios"
USERS_FILE: Final = SCENARIOS / "ssh_users.txt"
PASSWORDS_FILE: Final = SCENARIOS / "ssh_passwords.txt"
TARGET: Final = "honeypot"
TASKS: Final = 4  # hydra parallel tasks (-t), fixed


def _load_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def load_users() -> list[str]:
    return _load_lines(USERS_FILE)


def load_passwords() -> list[str]:
    return _load_lines(PASSWORDS_FILE)


class SshBruteForceRunner(ContainerAttackRunner):
    family = AttackFamily.SSH_BRUTE_FORCE

    def service_for(self, episode: Episode) -> str:
        return ATTACKER_SERVICE

    def command(self, episode: Episode) -> str:
        tasks = int(episode.parameters.get("tasks", TASKS))
        target_ip = SERVICE_IP[TARGET]
        # The committed lists are inlined so no file needs mounting into the container. Every
        # pair is tried (no -f), so the attempt count is fixed. -I ignores any restore file.
        users = "\\n".join(load_users())
        passwords = "\\n".join(load_passwords())
        return (
            f"printf '{users}\\n' > /tmp/u && printf '{passwords}\\n' > /tmp/p && "
            f"hydra -I -L /tmp/u -P /tmp/p -t {tasks} ssh://{target_ip}"
        )
