# Source-visibility check (E1-14)

Ticket E1-14 (SCRUM-121). The visibility matrix in `knowledge/attack_families.yaml` (tag
`families-v1.0`, METHODS.md Changelog entry 1) is a prediction. H1's stratification depends on
what each source actually captures, so this check runs each family once on the real testbed and
compares observed traces with the prediction (risk #4).

Each family was run once with its implemented method (ADR-0003), and traces were counted per
source: **mqtt** from the attack's own MQTT evidence (flood publishes in `mqtt.log` for
`mqtt_publish_flood`; refused-auth lines in `broker.log` for `mqtt_brute_force`; none for the
others), **flows** from `flows.jsonl` (flows involving the attack's origin or target), and
**honeypot** from `cowrie.json`. Runs on 2026-10-07; the counts come from the five run folders
listed below.

## Predicted vs observed

| Family | Predicted (mqtt/flows/honeypot) | Observed | Trace counts (mqtt, flows, honeypot) | Run | Match |
|---|---|---|---|---|---|
| `ssh_brute_force` | no / yes / yes | no / yes / yes | 0, 9, 44 | 20261007T185829Z | ✓ |
| `port_scan` | no / yes / yes | no / yes / yes | 0, 9, 2 | 20261007T185652Z | ✓ |
| `mqtt_publish_flood` | yes / yes / no | yes / yes / no | 3000, 4, 0 | 20261007T185219Z | ✓ |
| `mqtt_brute_force` | yes / yes / no | yes / yes / no | 25, 27, 0 | 20261007T185517Z | ✓ |
| `syn_flood` | no / yes / no | no / yes / no | 0, 3, 0 | 20261007T190030Z | ✓ |
| `botnet` | no / yes / no | **not run** | — | — | pending (E1-12 provisional) |

Notes on the counts:

- `syn_flood`'s "flows = 3" is the device's flow count (the flood is a single flow to port 80
  carrying ~238k SYN packets, plus the device's two benign connections); see `docs/families/F6.md`.
- `port_scan` honeypot = 2 Cowrie events, including one `cowrie.session.connect` on port 22 (the
  connect scan completes the handshake, as ADR-0003 requires).
- `mqtt_brute_force`'s mqtt trace is the broker's refused-auth log, not `mqtt.log` (a refused
  CONNECT publishes nothing); the MQTT source keeps `broker.log` for this reason (E1-05).

## Mismatches and resolution

None among the five families run. Every observed cell equals the frozen prediction, so
`knowledge/attack_families.yaml` is **unchanged** and no METHODS.md changelog entry is needed.

`botnet` (F5) is not yet run: it replays a dataset slice that has not been obtained (E1-12 is
provisional, `docs/families/F5.md`). Its predicted visibility (flows only) is **unverified**;
this check must be repeated for F5 once the slice is provided, and this table updated.

## Stratification

`tests/test_families.py::test_stratification` passes on the matrix (unchanged): no family leaves
traces in all three sources, four families leave traces in exactly two, one (`syn_flood`) in
exactly one, and MQTT and the honeypot each see at least two families. The observed results are
consistent with the rule; the one unverified family (`botnet`) is predicted one-source (flows),
which does not affect the rule's satisfaction.
