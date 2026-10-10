# Pilot repeatability (E1-15, re-run with all six families by E1-17)

Before the expensive corpus run, the mixed pilot schedule (`schedules/pilot.yaml`) is run twice
from `make reset` to show the testbed is reproducible, and the testbed's peak memory is measured
with Ollama stopped (§4.2). First done for five families under E1-15 (SCRUM-124); **re-run here
for all six families, adding botnet (F5), under E1-17 (SCRUM-130)** once the CICIoT2023 slice was
available (E1-12). The figures below are the six-family re-run on 2026-10-10.

- **Run 1:** `20261010T174834Z`  ·  **Run 2:** `20261010T181118Z`  (both in `data/pilot/`)
- Both runs are marked **valid** (not aborted) in their `execution_log.jsonl`, and all **six**
  attack episodes exited 0 (status `ok`). The isolation-gate control probe passed on both runs
  (stable Wi-Fi, not the iPhone hotspot that aborted the earlier attempt).

## Peak testbed memory (Ollama stopped)

**350.6 MiB**, the peak of the summed container memory sampled every 5 s across the whole of
run 1 (16 containers: broker, MQTT logger, honeypot, four emulators, the attacker, seven capture
sidecars). Far below the 16 GB budget (§4.2), so Ollama and the testbed still must not run at the
same time, but the testbed alone is comfortable.

## Repeatability of attack signals

Each attack family's raw event counts per source, compared between the two runs against the
family tolerance in `tests/attack_tolerance.yaml`. **Every difference is within tolerance.**

| Episode | Family | Source | Run 1 | Run 2 | Within tolerance |
|---|---|---|---|---|---|
| ep-f1-flood | mqtt_publish_flood | mqtt (flood msgs) | 3000 | 3000 | yes |
| ep-f1-flood | mqtt_publish_flood | flows (device `iot-temp-01`) | 31 | 31 | yes |
| ep-f2-mqttbrute | mqtt_brute_force | mqtt (refused auth) | 25 | 25 | yes |
| ep-f2-mqttbrute | mqtt_brute_force | flows (device `iot-temp-01`) | 31 | 31 | yes |
| ep-f3-portscan | port_scan | flows (attacker) | 19 | 19 | yes |
| ep-f3-portscan | port_scan | honeypot | 46 | 46 | yes |
| ep-f4-sshbrute | ssh_brute_force | flows (attacker) | 19 | 19 | yes |
| ep-f4-sshbrute | ssh_brute_force | honeypot | 46 | 46 | yes |
| ep-f6-synflood | syn_flood | flows (device `iot-cam-01`) | 45 | 43 | yes |
| ep-f6-synflood | syn_flood | packets (SYN to :80) | 223,858 | 232,958 | yes |
| ep-f5-botnet | botnet | flows (to C2 `192.0.2.1`) | 37 | 37 | yes |
| ep-f5-botnet | botnet | packets (to C2 `192.0.2.1`) | 9,955 | 9,955 | yes |

Benign MQTT messages over the whole run (telemetry + status, excluding the flood topic):
**744** vs **614**. Benign volume is time-driven and seeded with per-run jitter, bursts and
reconnects (E1-05), not part of the frozen attack ground truth, so it is not in the attack
tolerance gate; the 17.5 % spread is inside the benign profile's own ±25 % design envelope
(`testbed/profiles/benign.yaml`).

### How the counts are scoped

These are whole-run per-host totals, not per-episode-window counts:

- The two attacker-origin families (`port_scan`, `ssh_brute_force`) share the attacker host and
  the honeypot, so their "flows (attacker)" and "honeypot" rows are the combined totals for both
  episodes (19 and 46 in both runs).
- The two device-origin MQTT families share `iot-temp-01`, so their "flows (device)" row is that
  device's whole-run flow count (31).
- `syn_flood` (F6) and `botnet` (F5) both target `iot-cam-01`, so F6's "flows (device
  `iot-cam-01`)" row (45 / 43) counts that device's whole-run flows, which now include F5's
  replay as well as the SYN flood. F5's own row isolates the botnet by counting flows and packets
  to the retargeted C2 address `192.0.2.1` (TEST-NET-1, non-routable), which only the replay
  reaches. The SYN packet count is specific to the flood's destination port (:80).

For a repeatability check this is sufficient — the quantities are stable across runs — and exact
per-episode attribution by window is done at labelling time (E2-04), not here.

## Conclusion

The testbed is reproducible across all six families: two runs of the mixed pilot gave identical
or near-identical raw counts for every source of every family. The only non-identical attack
figures are the SYN flood's flows (45 vs 43) and packet volume (223,858 vs 232,958, ~3.9 %), both
inside the `syn_flood` tolerance; botnet (F5) was byte-stable (37 flows, 9,955 packets in both
runs, as expected from a fixed pcap replay). Benign MQTT volume varied within its ±25 % design
envelope (744 vs 614), as its jitter and bursts are meant to. The pilot data is stored under
`data/pilot/` and marked NOT FOR EVALUATION.
