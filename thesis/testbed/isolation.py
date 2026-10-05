"""The isolation gate: no attack starts unless the testbed is proven isolated (record §6.11).

`isolation_check()` runs `scripts/check_isolation.sh` (E0-07) against the run that is up and
appends its result to that run's `execution_log.jsonl`. Only exit code 0 counts as a pass. Any
other exit code, a timeout, or a script that cannot be started counts as a fail.

`require_isolation()` is the refusal path: the runner entry point calls it before it creates any
attack container, and it exits non-zero on a fail. `python -m thesis.testbed.isolation` runs the
same gate on its own.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import structlog
from pydantic import BaseModel, ConfigDict

REPO_ROOT: Final = Path(__file__).resolve().parent.parent.parent
SCRIPT: Final = REPO_ROOT / "scripts" / "check_isolation.sh"
RAW_DIR: Final = REPO_ROOT / "data" / "raw"
EXECUTION_LOG: Final = "execution_log.jsonl"
# Three probes per container, each with 2-second timeouts, plus the probe image pull.
TIMEOUT_S: Final = 300.0


class IsolationResult(BaseModel):
    """One isolation check. `passed` is true only when the script exited 0 in time."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    passed: bool
    exit_code: int | None
    timed_out: bool
    utc_ts: str
    run_id: str | None


def current_run_id(raw_dir: Path = RAW_DIR) -> str | None:
    """The run id written by `make up`, or None when no run is up."""
    marker = raw_dir / ".current_run"
    if not marker.is_file():
        return None
    return marker.read_text(encoding="utf-8").strip() or None


def _run_script(script: Path, timeout_s: float) -> tuple[int | None, bool]:
    """Run the script in its own process group, so a timeout also kills its docker children."""
    try:
        proc = subprocess.Popen(["bash", str(script)], start_new_session=True)
    except OSError:
        return None, False
    try:
        return proc.wait(timeout=timeout_s), False
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        return None, True


def _append(log_path: Path, result: IsolationResult) -> None:
    with log_path.open("a", encoding="utf-8") as sink:
        logger = structlog.wrap_logger(
            structlog.WriteLogger(sink),
            processors=[structlog.processors.JSONRenderer(sort_keys=True)],
            wrapper_class=structlog.BoundLogger,
        )
        logger.msg(
            event="isolation_check",
            result="pass" if result.passed else "fail",
            **result.model_dump(exclude={"passed"}),
        )


def isolation_check(
    *,
    script: Path = SCRIPT,
    raw_dir: Path = RAW_DIR,
    timeout_s: float = TIMEOUT_S,
) -> IsolationResult:
    """Run the egress check against the run that is up and log the result to that run.

    The result is appended to `<raw_dir>/<run_id>/execution_log.jsonl`. With no run up, the
    check fails without running, because there is no testbed to prove isolated.
    """
    run_id = current_run_id(raw_dir)
    exit_code, timed_out = (None, False) if run_id is None else _run_script(script, timeout_s)
    result = IsolationResult(
        passed=exit_code == 0 and not timed_out,
        exit_code=exit_code,
        timed_out=timed_out,
        utc_ts=datetime.now(UTC).isoformat(timespec="seconds"),
        run_id=run_id,
    )
    if run_id is not None:
        _append(raw_dir / run_id / EXECUTION_LOG, result)
    return result


def require_isolation(
    *,
    script: Path = SCRIPT,
    raw_dir: Path = RAW_DIR,
    timeout_s: float = TIMEOUT_S,
) -> IsolationResult:
    """Return the passing result, or exit with code 1 before any attack container exists."""
    result = isolation_check(script=script, raw_dir=raw_dir, timeout_s=timeout_s)
    if not result.passed:
        print(
            f"Isolation check failed (exit code {result.exit_code}, timed out "
            f"{result.timed_out}). No attack will start.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    require_isolation()
