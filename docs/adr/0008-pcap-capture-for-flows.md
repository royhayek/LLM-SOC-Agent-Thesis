# ADR-0008: Raw pcap capture with tcpdump, flows from the pcap

- Status: Accepted (2026-10-04)
- Date: 2026-10-04
- Ticket: SCRUM-70 [E0-07]

## Context

ADR-0002 put NFStream 6.6.0 in the capture sidecar. It left E0-07 to choose between NFStream reading the interface live and NFStream reading pcap files written by a capture tool. It also says a separate capture tool (it names tcpdump) needs ADR-0002 amended or a new ADR. This is that ADR. It changes only how the flow source is captured; the NFStream choice and its field mapping stand.

E0-07 first used live mode, and it loses flows. Evidence from the 5-minute benign run `20261004T154035Z`, where every MQTT publish opens its own TCP connection:

- MQTT carried 162 publishes, 15:40:37 to 15:45:53. The flows file holds 80 TCP flows to the broker.
- No flow starts after 15:43:37, so about the last 2 minutes are missing. Before that, 92 publishes gave 80 flows, so flows are missing mid-run too.
- After the traffic sources stopped, a 135 s wait (longer than the 120 s idle timeout) wrote no flow. The sidecar was then killed (exit 137).

In NFStream 6.6.0 (`meter.py`), a meter writes the flows left in its cache (`meter_cleanup`) only when its capture loop reaches end of input. A live interface never reaches it, so the open flows at shutdown are lost. In live mode NFStream also splits packets across several meter processes (one per CPU minus one), and each meter seems to advance its clock only with the packets it receives itself. That probably explains why flows do not expire once traffic stops, but it is not verified, because the C engine source is not shipped in the wheel.

Ground truth and the flow source (H1) cannot rest on a flow file that silently drops connections. Record §6.7 also asks for raw telemetry as immutable files, and a pcap is the raw form of the flow source.

## Decision

Option A below, chosen by Roy (2026-10-04).

- **tcpdump 4.99.3** (Debian bookworm package `tcpdump` 4.99.3-1), installed in the capture sidecar image. During a run it writes every packet on the broker's interface to `data/raw/<run_id>/flows/raw.pcap` (`tcpdump -i eth0 -w`, full snap length, no name resolution).
- **NFStream 6.6.0 reads that pcap after capture stops** (offline mode), with the ADR-0002 settings (`statistical_analysis=True`, the pinned `accounting_mode`) and its default timeouts. It writes `flows/flows.jsonl`. At end of file NFStream writes every flow still in its cache, so no flow is lost at the end of a run.
- `make down` stops the traffic sources, stops tcpdump so the pcap is closed, then runs NFStream on the pcap.
- The pcap stays in the run folder as raw telemetry, so the flows can be re-derived from it.

Two images used by E0-07 that no ADR names yet are recorded here too:

- **`python:3.12.11-slim-bookworm`**: base image of the capture sidecar, needed to install NFStream from PyPI (ADR-0002).
- **`busybox:1.37.0`**: a throwaway probe used only by `scripts/check_isolation.sh`. It joins each testbed container's network namespace to test reachability, then is removed. It is not a testbed service.

Licences: tcpdump BSD-3-Clause, BusyBox GPL-2.0. Both UNVERIFIED (not checked against the projects' licence files). Neither is linked into the `thesis` package.

## Alternatives considered

| Option | For | Against |
|---|---|---|
| **A. tcpdump writes a pcap; NFStream reads it offline** (proposed) | Complete flow file (flush at end of file); deterministic, so re-running NFStream on the same pcap gives the same flows; keeps a raw pcap as §6.7 raw telemetry; tcpdump is standard and widely cited | One more package in the sidecar image; disk use grows with traffic (benign MQTT is small); flows exist only after `make down`, not during the run |
| B. A pcap writer in Python's standard library (raw `AF_PACKET` socket) | No new package | Hand-written capture code in the measurement path, which an examiner can fairly question; must handle snap length, timestamps and the pcap format by hand |
| C. Keep live mode with `n_meters=1` | No new package; flows appear during the run | Does not fix the loss at shutdown (the cache is flushed only at end of input); the mid-run loss fix is untested |
| D. Keep live mode as it is | No change | Loses flows, shown above |

## Consequences

- The capture sidecar runs tcpdump during the run instead of NFStream. `testbed/capture/` gains the offline NFStream step, and `make down` runs it.
- Each run folder gains `flows/raw.pcap`. The README "Testbed" section and the run layout change accordingly.
- `docs/adr/0002-honeypot-and-flow-exporter.md` is not edited. Its Consequences already allow pcap input; this ADR records the capture tool.
- METHODS.md "Testbed capture settings (draft)" must not claim live capture or a drain wait.
- The flow count can now be checked against the connection count for a benign run, since no flow is lost at shutdown.
- Ruled out: live-mode NFStream for corpus runs, a hand-written capture tool, and any second capture tool.
