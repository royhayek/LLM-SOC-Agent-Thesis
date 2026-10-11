# Dataset card — IoT SOC corpus v1.0.0

The citable description of the frozen corpus (record §7.1). It is complete enough that someone
else could regenerate the corpus from the committed schedule, seed and configuration. Numbers come
from the integrity report (`docs/corpus/integrity_report.md`), the manifest
(`data/corpus-manifest.json`) and METHODS.md v1.1; they are not typed by hand.

## 1. Purpose

A labelled corpus of IoT security telemetry for evaluating an LLM-based SOC agent against two
baselines (hypotheses H1–H4). Each 60-second, device-keyed window is ground-truth labelled as one
of six attack families or benign, so detection, classification and safety can be scored on a
paired, reproducible dataset. The corpus is the measurement instrument; the agent is tested on it,
never trained on it.

## 2. Composition: devices, broker, honeypot, capture

Fully emulated testbed on one isolated internal Docker network (`10.77.0.0/24`), no published
ports (ADR-0007). Subject devices and infrastructure:

- **MQTT broker:** Mosquitto (`10.77.0.2`), authentication enabled for corpus runs (ADR-0003).
- **IoT devices (MQTT emulators):** `iot-temp-01` (`.21`), `iot-cam-01` (`.22`), `iot-hum-01`
  (`.23`), `iot-plug-01` (`.24`), each publishing telemetry and status.
- **Honeypot:** `hp-ssh-01` (`10.77.0.10`), Cowrie 3.1.0 (SSH only, BSD-3-Clause; ADR-0002),
  listening on port 22.
- **Attacker:** an isolated container (`10.77.0.30`) that runs the network attacks.
- **Capture:** one egress-only `tcpdump` sidecar per host, merged with `tcpslice`, then flows are
  derived offline with NFStream 6.6.0 (`statistical_analysis=True`); whole-network capture
  (ADR-0009). Per-host `raw.pcap`, `flows/flows.jsonl`, `mqtt/mqtt.log`, `mqtt/broker.log`,
  `honeypot/cowrie.json` are kept per run.

The isolation gate (probes from every container to the internet, the LAN gateway and the Docker
host gateway) passed before every chunk; no testbed container reached any external target.

## 3. Benign profiles

Four emulators publish benign MQTT continuously (E1-05, `testbed/profiles/benign.yaml`), seeded
and replayed from the run folder so counts are reproducible within a ±25 % tolerance:

- Telemetry periods 5, 7, 11, 13 s (jitter 1–3 s); status 60–120 s.
- QoS 0/1/2 mixed; payloads 90–200 B.
- Per emulator: 4 reconnects/h, 6 bursts/h of 3–5 messages, 2 refused logins/h.

Benign traffic never reaches the honeypot, so every honeypot-keyed window is an attack window
(§8 handling below).

## 4. Attack families, with generation method and licences

Six families (E1-02), each replaying published datasets or running standard tooling at fixed,
low-rate parameters — no custom exploit code (ADR-0003, Debian bookworm pinned versions):

| Family | Method | Tool (licence) |
|---|---|---|
| `ssh_brute_force` | SSH password guessing against the honeypot | THC-Hydra 9.4-1 (AGPL-3.0) |
| `port_scan` | TCP connect scan (`-sT`) against the honeypot | Nmap 7.93 (NPSL) |
| `mqtt_publish_flood` | MQTT publish flood to the broker | mosquitto_pub 2.0.11 (EPL/EDL) |
| `mqtt_brute_force` | MQTT credential guessing | mosquitto_pub 2.0.11 (EPL/EDL) |
| `syn_flood` | TCP SYN flood (fixed source port) | hping3 3.a2.ds2-10 (GPL-2.0) |
| `botnet` | Replay of a Mirai slice from CICIoT2023, retargeted to a non-routable C2 (`192.0.2.1`) | tcpreplay 4.4.3-1 (GPL-3.0+) |

Only `botnet` replays external data; its CICIoT2023 slice is not redistributed (manifest only —
the redistribution clause is `UNVERIFIED`). The retargeted destination `192.0.2.1` (TEST-NET-1) is
non-routable, so no real host is ever targeted.

Source-visibility per family (E1-14): `ssh_brute_force` and `port_scan` → flows + honeypot;
`mqtt_publish_flood` and `mqtt_brute_force` → MQTT + flows; `syn_flood` and `botnet` → flows only.

## 5. Schedule and seed

The corpus schedule is generated deterministically (E2-03): `python -m thesis.scenario.generate`
reads `config/corpus.yaml` and `schedules/corpus.seed` (seed **20261011**) and writes
`schedules/corpus-v1.0.0.yaml` — **142 attack episodes + 9 benign blocks**, every episode and
benign block carrying a `train` or `eval` split (E2-01, 70/30 per family, seeded before
generation). Episode durations vary over {120, 180, 240} s, 60-second aligned. Regenerating from
the same seed reproduces the schedule byte-for-byte.

## 6. Label derivation

Labels are derived mechanically from the executed schedule, never by hand (E2-04,
`thesis/labels/windows.py`): a (device, 60-second window) is labelled with a family when it
overlaps, by any non-zero duration, an executed episode of that family against that device
(half-open windows, UTC); otherwise benign. Window W = 60 s (`config/incident.yaml`, METHODS.md
§1). One Parquet label file per chunk in `data/labels/`.

## 7. Counts per family, benign and split

Window-level counts over the six run chunks (from the integrity report; **1360 labelled windows**
total: 778 benign + 582 attack). Per-family targets are the METHODS.md v1.1 per-family total
(eval 50 + train 22 = 72); all clear it.

| Family | Eval | Train | Total |
|---|---|---|---|
| ssh_brute_force | 67 | 30 | 97 |
| port_scan | 69 | 30 | 99 |
| mqtt_publish_flood | 66 | 31 | 97 |
| mqtt_brute_force | 67 | 30 | 97 |
| syn_flood | 65 | 29 | 94 |
| botnet | 69 | 29 | 98 |
| **Attack total** | **403** | **179** | **582** |
| Benign | — | — | **778** |

These are window-level counts, which overestimate the final bundle counts because empty windows
are dropped at assembly (E3-09 confirms the bundle-level numbers). They exceed the evaluation
target N_eval = 480 (300 attack + 180 benign) with margin, as designed (E2-02).

## 8. Known limitations

- **Emulated, not physical.** Devices are software emulators on Docker, not real IoT hardware;
  timing, firmware quirks and radio-layer effects of physical devices are absent.
- **Replayed traffic.** The `botnet` family is a replay of a published Mirai slice retargeted to a
  non-routable address, not live botnet behaviour; its flow shape is the dataset's, not this
  network's.
- **Honeypot windows are all positive.** No benign traffic reaches the honeypot, so every
  honeypot-keyed window is an attack window; detection metrics are reported both over all windows
  and without the honeypot-keyed ones, and every hypothesis test is repeated without them (§8,
  METHODS.md).

## 9. Version and manifest hash

- **Corpus:** `corpus-v1.0.0-rc` (release candidate; frozen as v1.0.0 by E2-09).
- **Files:** 156 (raw telemetry under `data/raw/corpus-v1.0.0-rc/` and labels under
  `data/labels/`).
- **Manifest:** `data/corpus-manifest.json`, SHA-256
  `869637b64cc5ad46a3bc7eadd8fba159602964d7112ba36946707b39783a88d8`
  (`data/corpus-manifest.sha256`). `python -m thesis.corpus.manifest verify` proves the data is
  unchanged; `python -m thesis.corpus.check` revalidates integrity (5/5 checks pass).
