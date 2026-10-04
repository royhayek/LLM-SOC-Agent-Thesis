"""Flow export: NFStream reads a run's pcap offline and writes one JSON line per flow.

ADR-0002 (NFStream settings) and ADR-0008 (pcap capture, offline flows). `make down` runs
this after tcpdump has closed the pcap. At end of file NFStream writes every flow still in
its cache, so no flow is lost at the end of a run.
"""

from __future__ import annotations

import json
import os
import sys

from nfstream import NFStreamer

PCAP_PATH = os.environ.get("PCAP_PATH", "/out/raw.pcap")
OUT_PATH = os.environ.get("FLOWS_PATH", "/out/flows.jsonl")

# ADR-0002: the per-flag TCP counters exist only with statistical_analysis=True.
STATISTICAL_ANALYSIS = True
# ADR-0002 leaves the choice to E0-07. 0 (link layer) is NFStream's default; see METHODS.md.
ACCOUNTING_MODE = 0
# NFStream's defaults, pinned so a change is visible here.
IDLE_TIMEOUT_S = 120
ACTIVE_TIMEOUT_S = 1800
# One meter process: with several, flow order and NFStream's `id` vary between runs on the
# same pcap. With one, re-running on the same pcap gives a byte-identical flows file.
N_METERS = 1


def main() -> int:
    streamer = NFStreamer(
        source=PCAP_PATH,
        statistical_analysis=STATISTICAL_ANALYSIS,
        accounting_mode=ACCOUNTING_MODE,
        idle_timeout=IDLE_TIMEOUT_S,
        active_timeout=ACTIVE_TIMEOUT_S,
        n_meters=N_METERS,
    )
    n = 0
    with open(OUT_PATH, "w", encoding="utf-8") as out:
        for flow in streamer:
            record = {k: getattr(flow, k) for k in flow.keys()}
            out.write(json.dumps(record, default=str) + "\n")
            n += 1
    print(f"{n} flows written to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
