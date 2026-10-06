"""Tests for the isolation gate (E1-01, record §6.11).

The fast tests replace `check_isolation.sh` with a stub script. The `slow` tests bring the real
testbed up with `make up`, so they need Docker running and Ollama stopped (16 GB machine).
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from thesis.testbed.isolation import (
    EXECUTION_LOG,
    RAW_DIR,
    REPO_ROOT,
    current_run_id,
    isolation_check,
    require_isolation,
)

RUN_ID = "20261005T000000Z"


def fake_run(tmp_path: Path, body: str) -> tuple[Path, Path]:
    """A raw dir with one run up, and a stub check script with the given body."""
    raw_dir = tmp_path / "raw"
    (raw_dir / RUN_ID).mkdir(parents=True)
    (raw_dir / ".current_run").write_text(RUN_ID + "\n", encoding="utf-8")
    script = tmp_path / "check.sh"
    script.write_text(f"#!/usr/bin/env bash\n{body}\n", encoding="utf-8")
    return raw_dir, script


def log_lines(raw_dir: Path) -> list[dict[str, object]]:
    text = (raw_dir / RUN_ID / EXECUTION_LOG).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def test_exit_zero_passes_and_is_logged(tmp_path: Path) -> None:
    raw_dir, script = fake_run(tmp_path, "exit 0")

    result = isolation_check(script=script, raw_dir=raw_dir)

    assert result.passed
    [line] = log_lines(raw_dir)
    assert line["event"] == "isolation_check"
    assert line["result"] == "pass"
    assert line["exit_code"] == 0
    assert line["run_id"] == RUN_ID


@pytest.mark.parametrize("code", [1, 2])
def test_non_zero_exit_fails(tmp_path: Path, code: int) -> None:
    raw_dir, script = fake_run(tmp_path, f"exit {code}")

    result = isolation_check(script=script, raw_dir=raw_dir)

    assert not result.passed
    assert log_lines(raw_dir)[0]["result"] == "fail"


def test_timeout_fails(tmp_path: Path) -> None:
    raw_dir, script = fake_run(tmp_path, "sleep 30; exit 0")

    result = isolation_check(script=script, raw_dir=raw_dir, timeout_s=0.5)

    assert not result.passed
    assert result.timed_out
    assert log_lines(raw_dir)[0]["timed_out"] is True


def test_no_run_up_fails_without_running(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    script = tmp_path / "check.sh"
    script.write_text("#!/usr/bin/env bash\ntouch ran\nexit 0\n", encoding="utf-8")

    assert not isolation_check(script=script, raw_dir=raw_dir).passed
    assert not (tmp_path / "ran").exists()


def test_require_isolation_exits_non_zero_on_fail(tmp_path: Path) -> None:
    raw_dir, script = fake_run(tmp_path, "exit 1")

    with pytest.raises(SystemExit) as exc:
        require_isolation(script=script, raw_dir=raw_dir)
    assert exc.value.code == 1


# --- Against the real testbed ------------------------------------------------------------


def docker(*args: str) -> str:
    return subprocess.run(
        ["docker", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def all_container_ids() -> set[str]:
    return set(docker("ps", "-a", "--format", "{{.ID}}").split())


@pytest.fixture(scope="module")
def testbed() -> Iterator[str]:
    """Bring the testbed up for this module and yield the run id."""
    subprocess.run(["make", "up"], cwd=REPO_ROOT, check=True)
    try:
        run_id = current_run_id()
        assert run_id is not None
        yield run_id
    finally:
        subprocess.run(["make", "down"], cwd=REPO_ROOT, check=True)


@pytest.mark.slow
def test_internal_testbed_passes_and_is_logged(testbed: str) -> None:
    result = isolation_check()

    assert result.passed
    lines = (RAW_DIR / testbed / EXECUTION_LOG).read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[-1])["result"] == "pass"


@pytest.mark.slow
def test_non_internal_network_refuses_the_run(testbed: str) -> None:
    # A container with its own network: capture sidecars share another container's network
    # namespace (ADR-0009), and Docker refuses to connect those to a second network.
    container = docker(
        "ps",
        "--filter",
        "label=com.docker.compose.project=thesis-testbed",
        "--filter",
        "label=com.docker.compose.service=honeypot",
        "--format",
        "{{.Names}}",
    ).split()[0]
    docker("network", "connect", "bridge", container)
    try:
        before = all_container_ids()
        entry = subprocess.run([sys.executable, "-m", "thesis.testbed.isolation"], cwd=REPO_ROOT)
        after = all_container_ids()
    finally:
        docker("network", "disconnect", "bridge", container)

    assert entry.returncode != 0
    assert after == before, "a container was created although the isolation check failed"
    lines = (RAW_DIR / testbed / EXECUTION_LOG).read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[-1])["result"] == "fail"
