"""Tests for whole-network flow capture (E1-16, ADR-0009).

Fast tests check the compose file and the Makefile: every host on the testbed network has one
egress-only capture sidecar. The `slow` test runs the real testbed: no packet is captured
twice, an emulator-to-honeypot connection reaches flows.jsonl, and the isolation check passes.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE = REPO_ROOT / "docker-compose.yml"
MAKEFILE = REPO_ROOT / "Makefile"
CAPTURE_PREFIX = "capture-"


def _services() -> dict[str, Any]:
    services: dict[str, Any] = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))["services"]
    return services


def _sidecars() -> dict[str, dict[str, Any]]:
    return {n: s for n, s in _services().items() if n.startswith(CAPTURE_PREFIX)}


def _hosts_on_testbed() -> set[str]:
    """Services with their own interface on the testbed network: the traffic sources."""
    return {n for n, s in _services().items() if "testbed" in (s.get("networks") or {})}


def test_every_testbed_host_has_one_capture_sidecar() -> None:
    covered = [s["network_mode"].removeprefix("service:") for s in _sidecars().values()]
    assert sorted(covered) == sorted(set(covered)), "a host has two sidecars"
    assert set(covered) == _hosts_on_testbed()


def test_sidecars_capture_egress_only_into_unique_files() -> None:
    files = []
    for name, sidecar in _sidecars().items():
        cmd = sidecar["command"]
        assert cmd[0] == "tcpdump", name
        assert cmd[cmd.index("-Q") + 1] == "out", f"{name} must capture outbound packets only"
        assert cmd[cmd.index("-i") + 1] == "eth0", name
        assert cmd[cmd.index("-s") + 1] == "0", f"{name} must keep full packets"
        files.append(cmd[cmd.index("-w") + 1])
        assert sidecar["restart"] == "no", f"{name}: a restart would overwrite its pcap"
    assert len(files) == len(set(files)), "two sidecars write the same pcap"


def test_makefile_stops_and_checks_every_sidecar() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    match = re.search(r"^CAPTURES := (.*?)(?<!\\)\n", text, re.M | re.S)
    assert match, "Makefile has no CAPTURES list"
    listed = set(match.group(1).replace("\\\n", " ").split())
    assert listed == set(_sidecars())


def test_capture_image_pins_its_tools() -> None:
    dockerfile = (REPO_ROOT / "testbed" / "capture" / "Dockerfile").read_text(encoding="utf-8")
    assert "tcpdump=4.99.3-1" in dockerfile
    assert "tcpslice=1.5-1" in dockerfile


# --- Real testbed (slow) ------------------------------------------------------------------


def _run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, check=True, text=True, capture_output=True, **kw)


@pytest.mark.slow
def test_benign_run_captures_every_packet_once() -> None:
    """E1-16 acceptance criteria, on a short benign run with one emulator-to-honeypot connection.
    Ollama must be stopped; run under `caffeinate -is` on macOS.
    """
    current = REPO_ROOT / "data" / "raw" / ".current_run"
    assert not current.exists(), "a run is already up"
    _run(["make", "up"])
    run_id = current.read_text(encoding="utf-8").strip()
    try:
        time.sleep(20)  # benign traffic starts; every sidecar is up
        # One TCP connection from an emulator to the honeypot's SSH port, inside the testbed.
        subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "emulator-temp",
                "sh",
                "-c",
                "nc -w 3 honeypot 22 </dev/null",
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
        )
        isolation = subprocess.run(
            ["bash", "scripts/check_isolation.sh"], cwd=REPO_ROOT, capture_output=True
        )
        time.sleep(5)
    finally:
        _run(["make", "down"])
    assert isolation.returncode == 0, isolation.stdout[-2000:]

    flows_dir = REPO_ROOT / "data" / "raw" / run_id / "flows"
    lines = _run(
        [
            "docker", "run", "--rm", "--network", "none", "-v", f"{flows_dir}:/out",
            "--entrypoint", "tcpdump", "thesis-testbed-capture:e1-16",
            "-tt", "-n", "-r", "/out/raw.pcap", "ip",
        ]
    ).stdout.splitlines()  # fmt: skip
    assert lines, "the merged pcap holds no IPv4 packet"
    assert len(lines) == len(set(lines)), "a packet was captured twice"

    flows = [json.loads(line) for line in (flows_dir / "flows.jsonl").read_text().splitlines()]
    assert any(
        {f["src_ip"], f["dst_ip"]} == {"10.77.0.21", "10.77.0.10"}
        and 22 in (f["src_port"], f["dst_port"])
        for f in flows
    ), "no flow between emulator-temp and the honeypot's SSH port"


@pytest.mark.slow
def test_merge_skips_hosts_that_sent_nothing(tmp_path: Path) -> None:
    """tcpslice 1.5 stops on a header-only pcap (a host that sent nothing); merge.sh must skip
    it, and still write a valid raw.pcap when every host was silent. Needs the capture image
    (`make up` builds it); runs with no network.
    """
    # idle.pcap: header only. busy.pcap: three refused TCP connects on loopback, a SYN and a
    # RST each, so 6 packets. The image has bash but no ping.
    script = r"""
        set -e; mkdir -p /out/hosts; cd /out/hosts
        timeout 2 tcpdump -i lo -c 1 -w idle.pcap 'not ip' 2>/dev/null || true
        (sleep 0.5; for i in 1 2 3; do (exec 3<>/dev/tcp/127.0.0.1/9) 2>/dev/null || true; done) &
        timeout 3 tcpdump -i lo -w busy.pcap 2>/dev/null || true
        cd /app && sh merge.sh
        tcpdump -r /out/raw.pcap 2>/dev/null | wc -l
        rm /out/hosts/busy.pcap /out/raw.pcap && sh merge.sh
        tcpdump -r /out/raw.pcap 2>/dev/null | wc -l
    """
    lines = _run(
        [
            "docker", "run", "--rm", "--network", "none", "-v", f"{tmp_path}:/out",
            "--entrypoint", "bash", "thesis-testbed-capture:e1-16", "-c", script,
        ]
    ).stdout.splitlines()  # fmt: skip
    assert lines[0].startswith("merged 1 per-host pcaps")  # the idle pcap is skipped
    assert int(lines[1]) == 6
    assert lines[2].startswith("merged 0 per-host pcaps")  # every host silent, no error
    assert int(lines[3]) == 0  # raw.pcap is a valid, header-only pcap
