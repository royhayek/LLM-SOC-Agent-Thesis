"""Capture sidecar: NFStream on the broker's network namespace, one JSON line per flow.

Settings pinned by ADR-0002. Runs in its own container, not in the thesis package.
"""

from __future__ import annotations

import json
import os
import signal
import sys
from typing import Any

from nfstream import NFStreamer

INTERFACE = os.environ.get("CAPTURE_INTERFACE", "eth0")
OUT_PATH = os.environ.get("FLOWS_PATH", "/out/flows.jsonl")

# ADR-0002: the per-flag TCP counters exist only with statistical_analysis=True.
STATISTICAL_ANALYSIS = True
# ADR-0002 leaves the choice to E0-07. 0 (link layer) is NFStream's default; see README.
ACCOUNTING_MODE = 0


def _stop(signum: int, frame: Any) -> None:
    raise KeyboardInterrupt


def main() -> int:
    signal.signal(signal.SIGTERM, _stop)
    streamer = NFStreamer(
        source=INTERFACE,
        statistical_analysis=STATISTICAL_ANALYSIS,
        accounting_mode=ACCOUNTING_MODE,
    )
    with open(OUT_PATH, "a", encoding="utf-8") as out:
        try:
            for flow in streamer:
                record = {k: getattr(flow, k) for k in flow.keys()}
                out.write(json.dumps(record, default=str) + "\n")
                out.flush()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
