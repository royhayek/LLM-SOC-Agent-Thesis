# thesis

MSc thesis project: **LLM-Based Autonomous SOC Agent for IoT Cyberattack Detection and Response**.
Roy EL HAYEK, MSc 2 Artificial Intelligence, ECE Paris.

A pipeline turns three IoT telemetry streams (MQTT, network flows, honeypot logs) into one validated verdict plus a recommended action. A measurement rig tests four hypotheses against two baselines. The agent recommends and never executes.

The repository and package are named `thesis` until a system name is chosen (ticket E11-14).

## Where to look

| What | Where |
|---|---|
| Rules for working in this repo | `docs/WORKING_RULES.md` |
| Definition of Done and Ready | `docs/DOD.md` |
| All tickets | `docs/planning/backlog_full.md` |
| Ticket reference to Jira key | `docs/planning/jira_key_map.md` |
| Source documents (proposal, record, architecture) | `docs/source/` |
| Architecture decisions | `docs/adr/` |
| Notes the thesis will cite | `docs/thesis_notes.md` |

## Testbed

A benign-only, fully emulated IoT testbed in Docker Compose (`docker-compose.yml`): a Mosquitto broker, four MQTT emulators, an MQTT logger, a Cowrie SSH honeypot and a capture sidecar on the broker's network namespace (tcpdump, then NFStream; ADR-0002, ADR-0008). The only network is internal and no port is published.

| Command | What it does |
|---|---|
| `make up` | Starts the testbed. Raw logs for this run go to `data/raw/<run_id>/` |
| `scripts/check_isolation.sh` | Checks that no container reaches 1.1.1.1, the host LAN gateway or Docker's host gateway. Exit 0 only if none does. Run it before any attack tooling. Its output is saved to the run folder |
| `make down` | Stops the traffic sources, then the capture, then the testbed, and derives `flows.jsonl` from the run's pcap. Keeps the run's raw logs |
| `make reset` | Removes the testbed's containers, network and volumes. Raw logs on disk are kept |

`<run_id>` is the UTC start time, for example `20261004T152803Z`. Each run folder holds:

| File | Source | Format |
|---|---|---|
| `mqtt/mqtt.log` | every message on the broker | one line per message: ISO 8601 time, topic, JSON payload |
| `flows/raw.pcap` | tcpdump 4.99.3 on the broker's interface | every packet, full length |
| `flows/flows.jsonl` | NFStream 6.6.0 reading `raw.pcap` at `make down` | one JSON object per flow, all `NFlow` fields |
| `honeypot/cowrie.json` | Cowrie 3.1.0 | one JSON event per line. Empty under benign traffic, by design |
| `isolation_check.log` | `scripts/check_isolation.sh` | the output of every isolation check run during the run |

NFStream runs with `statistical_analysis=True`, `accounting_mode=0` (link-layer bytes) its default timeouts and one meter process (so re-running on the same pcap gives a byte-identical flows file), pinned in `testbed/capture/flows.py`. METHODS.md, "Testbed capture settings (draft)", records these choices. `docker run --rm --entrypoint python thesis-testbed-capture:e0-07 check_direction.py` checks on a test pcap that a flow's `src_ip` is the sender of its first packet (ADR-0002).

## Resources

On a 16 GB machine, **stop Ollama before `make up`** (quit the Ollama app, or stop the `ollama serve` process; `ollama stop` only unloads a model). The testbed and the local model never run at the same time (record §4.2).

Measured peak memory of the testbed: **50 MiB** across all eight containers (49.4 MiB, the sum of `docker stats` at the busiest of 41 samples over a 5-minute benign run on 2026-10-04, Docker Desktop 27.3.1 on an M2; the samples are in that run's `docker_stats.csv`). Cowrie takes 43 MiB; every other container stays under 2 MiB. The flow export at `make down` runs after the testbed has stopped and peaked at 71 MiB for that run's pcap. These figures exclude the Docker Desktop VM itself.

## Status

Sprint 0 (2–16 Oct 2026): EPIC-0, Project Foundation & Engineering Baseline.
