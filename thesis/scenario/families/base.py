"""Shared machinery for the attack families (E1-08..E1-13).

Every family drives one standard tool inside an already-running testbed container (ADR-0003):
device-origin families (flood, credential guessing, botnet) run in the compromised device's
own container, so the traffic keys to device D (record §4.1); external-origin families (scan,
SSH guessing, SYN flood) run in the `attacker` container, an isolated host on the testbed
network. Nothing new is started mid-run, so the containers the E1-01 isolation gate checked
are the ones that act.

`ContainerAttackRunner` launches the tool with `docker exec` at the episode's start offset and,
at its end offset, stops it for good. `docker exec` gives the shell its own process group, whose
pid is written to a per-episode file; `stop()` signals that whole group, so an attack and any
child can never outlive its episode (record §4.1 gotcha). Every family is bounded to finish
within its episode, so a normal run returns 0; the runner marks the run invalid on any non-zero
exit, and the kill path is a safety net.
"""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path
from typing import Final

from thesis.scenario.runner import AttackHandle
from thesis.scenario.schedule import Episode

COMPOSE_PROJECT: Final = "thesis-testbed"

# Subject device id -> its Docker Compose service. The honeypot and the attacker container are
# the targets and origin of the external-origin families; the four emulators are the devices.
DEVICE_SERVICE: Final[dict[str, str]] = {
    "hp-ssh-01": "honeypot",
    "iot-temp-01": "emulator-temp",
    "iot-cam-01": "emulator-cam",
    "iot-hum-01": "emulator-hum",
    "iot-plug-01": "emulator-plug",
}
ATTACKER_SERVICE: Final = "attacker"

# Fixed testbed IPs (docker-compose.yml). Targets are addressed by IP so no name resolution is
# needed inside the attack container.
SERVICE_IP: Final[dict[str, str]] = {
    "honeypot": "10.77.0.10",
    "emulator-temp": "10.77.0.21",
    "emulator-cam": "10.77.0.22",
    "emulator-hum": "10.77.0.23",
    "emulator-plug": "10.77.0.24",
    "attacker": "10.77.0.30",
}


def container_id(service: str, project: str = COMPOSE_PROJECT) -> str:
    """The running container id of a compose service, by its compose labels."""
    out = subprocess.run(
        [
            "docker",
            "ps",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--filter",
            f"label=com.docker.compose.service={service}",
            "--format",
            "{{.ID}}",
        ],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.split()
    if not out:
        raise RuntimeError(f"no running container for service {service!r}")
    return out[0]


class _ExecHandle:
    """A running `docker exec`. `stop()` signals the attack's process group, returns its status."""

    def __init__(self, container: str, pgid_file: str, proc: subprocess.Popen[bytes]) -> None:
        self._container = container
        self._pgid_file = pgid_file
        self._proc = proc

    def stop(self) -> int:
        # The tool may have finished on its own (bounded) or still be running. Signal its whole
        # process group, then reap the local docker-exec client, which exits with the tool's code.
        kill = (
            f"p=$(cat {self._pgid_file} 2>/dev/null); "
            f'if [ -n "$p" ]; then kill -TERM -"$p" 2>/dev/null; sleep 1; '
            f'kill -KILL -"$p" 2>/dev/null; fi; rm -f {self._pgid_file}; true'
        )
        subprocess.run(
            ["docker", "exec", self._container, "sh", "-c", kill],
            check=False,
            capture_output=True,
        )
        try:
            return self._proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            return self._proc.wait()


class ContainerAttackRunner:
    """Base class: run `command(episode)` in `service_for(episode)`'s container at episode start.

    Subclasses set `family` and implement `service_for` and `command`. `command` is a shell
    string run as a process-group leader; it must finish within the episode on its own.
    """

    def service_for(self, episode: Episode) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def command(self, episode: Episode) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def start(self, episode: Episode, run_dir: Path) -> AttackHandle:
        container = container_id(self.service_for(episode))
        pgid_file = f"/tmp/thesis-attack-{episode.id}-{uuid.uuid4().hex[:8]}.pgid"
        # `docker exec` gives the shell its own process group (pid == pgid), so $$ is the group
        # id: stop() signals the whole group, and the shell still returns the command's real
        # exit code. (setsid is avoided: busybox setsid has no -w, so it would mask that code,
        # and `exec` is avoided so a compound command like a loop runs.)
        shell = f"echo $$ > {pgid_file}; {self.command(episode)}"
        proc = subprocess.Popen(
            ["docker", "exec", container, "sh", "-c", shell],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return _ExecHandle(container, pgid_file, proc)
