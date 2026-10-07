# Pilot repeatability (E1-15)

Ticket E1-15 (SCRUM-124). Before the expensive corpus run, the mixed pilot schedule
(`schedules/pilot.yaml`) was run twice from `make reset` to show the testbed is reproducible,
and the testbed's peak memory was measured with Ollama stopped (§4.2). Runs on 2026-10-07.

- **Run 1:** `20261007T202320Z`  ·  **Run 2:** `20261007T203707Z`  (both in `data/pilot/`)
- Both runs are marked **valid** in their `execution_log.jsonl`, and all five attack episodes
  exited 0 (status `ok`).
- **Botnet (F5) is omitted** from the pilot: it is provisional and cannot run until its dataset
  slice is provided (E1-12). Re-run the pilot with F5 once it is implemented.

## Peak testbed memory (Ollama stopped)

**462 MiB**, the peak of the summed container memory sampled every 5 s across the whole of run 1
(16 containers: broker, MQTT logger, honeypot, four emulators, the attacker, seven capture
sidecars). Far below the 16 GB budget (§4.2), so Ollama and the testbed still must not run at
the same time, but the testbed alone is comfortable.

## Repeatability of attack signals

Each attack family's raw event counts per source, compared between the two runs against the
family tolerance in `tests/attack_tolerance.yaml`. **Every difference is within tolerance.**

| Episode | Family | Source | Run 1 | Run 2 | Within tolerance |
|---|---|---|---|---|---|
| ep-f1-flood | mqtt_publish_flood | mqtt (flood msgs) | 3000 | 3000 | yes |
| ep-f1-flood | mqtt_publish_flood | flows (device) | 31 | 31 | yes |
| ep-f2-mqttbrute | mqtt_brute_force | mqtt (refused auth) | 25 | 25 | yes |
| ep-f2-mqttbrute | mqtt_brute_force | flows (device) | 31 | 31 | yes |
| ep-f3-portscan | port_scan | flows (attacker) | 19 | 19 | yes |
| ep-f3-portscan | port_scan | honeypot | 46 | 46 | yes |
| ep-f4-sshbrute | ssh_brute_force | flows (attacker) | 19 | 19 | yes |
| ep-f4-sshbrute | ssh_brute_force | honeypot | 46 | 46 | yes |
| ep-f6-synflood | syn_flood | flows (device) | 6 | 6 | yes |
| ep-f6-synflood | syn_flood | packets (SYN to :80) | 238418 | 240238 | yes |

Benign MQTT messages over the whole run (telemetry + status, excluding the flood topic):
**467** vs **466** — the seeded benign profile is reproducible (E1-05).

### How the counts are scoped

These are whole-run per-host totals, not per-episode-window counts: the two attacker-origin
families (`port_scan`, `ssh_brute_force`) share the attacker host and the honeypot, so their
"flows (attacker)" and "honeypot" rows are the combined totals for both episodes (19 and 46 in
both runs); likewise the two device-origin MQTT families share `iot-temp-01`, so their "flows
(device)" row is that device's whole-run flow count (31). The SYN packet count is specific to
the flood's destination port. For a repeatability check this is sufficient — the quantities are
stable across runs — and exact per-episode attribution by window is done at labelling time
(E2-04), not here.

## Conclusion

The testbed is reproducible: two runs of the mixed pilot gave identical or near-identical raw
counts for every source of every family (the only non-identical figure is the SYN flood's packet
volume, 238,418 vs 240,238, ~0.8 %, inside its 20 % tolerance), and benign traffic matched to
within one message. The pilot data is stored under `data/pilot/` and marked NOT FOR EVALUATION.
