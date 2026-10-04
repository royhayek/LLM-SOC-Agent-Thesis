# ADR-0002: Honeypot and flow-exporter software

- Status: Accepted (2026-10-04)
- Date: 2026-10-04
- Ticket: SCRUM-119 [E0-14]

## Context

The record fixes "one honeypot" and "a capture sidecar" for the testbed (record §8, ticket 7) but names no software. Both choices decide what the honeypot and flow sources can see, so they bound H1 and the reduction fields of record §4.4. E0-05 (reduction policy), E0-07 (compose testbed) and E1-04 (attack generation) wait on this ADR.

Criteria. An option that fails C1 to C4 is out; C5 to C7 rank the rest.

| # | Criterion | Source |
|---|---|---|
| C1 | Runs as a Linux container on 16 GB Apple Silicon (linux/arm64), alongside the testbed and with Ollama stopped | Record §4, §4.2 |
| C2 | Honeypot: records SSH authentication attempts (username, password, success or failure) and the commands typed in the session | Record §3.2, §9; ticket technical notes |
| C3 | Flow exporter: emits per flow destination IP, destination port, bytes in each direction, protocol, TCP flags and duration | Record §4.4; ticket technical notes |
| C4 | Open-source licence that allows use and modification in an academic project | DoD (no unrecorded technology) |
| C5 | Maintained: a release in the last 12 months | Reproducibility, record §4.2 |
| C6 | Structured output (JSON or typed records) that a parser can read without screen-scraping | E3 parsers |
| C7 | Smallest footprint that meets C1 to C6: one process, no extra service | Working rules ("never add") |

Versions, licences and release dates below were read from each project's repository and package index on 2026-10-04.

## Decision

**Honeypot: Cowrie 3.1.0** (BSD-3-Clause), official image `cowrie/cowrie:3.1.0`, JSON log output (`cowrie.json`), SSH only.

**Flow exporter: NFStream 6.6.0** (LGPL-3.0), from PyPI, with `statistical_analysis=True` so the per-flag TCP packet counters are emitted. It runs inside the capture sidecar container, not in the `thesis` package.

Each §4.4 aggregate maps to a field the tool emits, or is derived from emitted fields by the formula given.

**Flows (NFStream 6.6.0).** D is the bundle's subject device (record §4.1). "Out" means bytes sent by D.

| §4.4 aggregate | Emitted field(s) | Emitted or derived | Formula |
|---|---|---|---|
| count | one `NFlow` record per flow | derived | number of flows in the window |
| unique dst IPs | `dst_ip` | derived | count of distinct `dst_ip` |
| unique dst ports | `dst_port` | derived | count of distinct `dst_port` |
| bytes out | `src_ip`, `src2dst_bytes`, `dst2src_bytes` | derived | sum of `src2dst_bytes` where `src_ip` = D, plus `dst2src_bytes` where `dst_ip` = D |
| bytes in | `src_ip`, `src2dst_bytes`, `dst2src_bytes` | derived | sum of `dst2src_bytes` where `src_ip` = D, plus `src2dst_bytes` where `dst_ip` = D |
| protocol mix | `protocol` (IANA number) | derived | count of flows per `protocol` value |
| SYN-only ratio | `protocol`, `src2dst_syn_packets`, `src2dst_ack_packets` | derived | flows with `protocol` = 6 and `src2dst_syn_packets` ≥ 1 and `src2dst_ack_packets` = 0, divided by flows with `protocol` = 6 |
| duration stats | `bidirectional_duration_ms` | derived | statistics over `bidirectional_duration_ms`; which statistics is E0-05's choice |

The flow exemplars (top 5 by detector score) need the detector's score, not an exporter field. The detector's features come from the same `NFlow` records.

**Honeypot (Cowrie 3.1.0).** Every event carries `eventid`, `session`, `src_ip` and `timestamp` (Cowrie `docs/OUTPUT.rst`).

| §4.4 aggregate | Emitted field(s) | Emitted or derived | Formula |
|---|---|---|---|
| session count | `session` on `cowrie.session.connect` | derived | count of distinct `session` |
| unique source IPs | `src_ip` | derived | count of distinct `src_ip` |
| auth attempts | `eventid` = `cowrie.login.failed`, `cowrie.login.success` | derived | count of `cowrie.login.failed` plus count of `cowrie.login.success` |
| success / fail | `eventid` = `cowrie.login.success` / `cowrie.login.failed` | derived | the two counts separately |

The honeypot exemplars (up to 3 command sequences, hard-truncated) come from `input` on `cowrie.command.input` events, grouped by `session`. `cowrie.command.failed` carries `input` for commands the emulated shell does not implement, so both events are read.

**MQTT.** The MQTT aggregates of §4.4 come from the broker and the emulators, not from either tool chosen here. No row is mapped.

**Sample lines from each tool's documentation.**

NFStream, the printed flow in the project README (v6.6.0), shortened here to the fields mapped above:

```
NFlow(id=0, expiration_id=0, src_ip='192.168.43.18', src_mac='30:52:cb:6c:9c:1b', src_oui='30:52:cb', src_port=52066, dst_ip='66.220.156.68', dst_mac='98:0c:82:d3:3c:7c', dst_oui='98:0c:82', dst_port=443, protocol=6, ip_version=4, vlan_id=0, tunnel_id=0, bidirectional_first_seen_ms=1472393122365, bidirectional_last_seen_ms=1472393123665, bidirectional_duration_ms=1300, bidirectional_packets=19, bidirectional_bytes=5745, src2dst_first_seen_ms=1472393122365, src2dst_last_seen_ms=1472393123408, src2dst_duration_ms=1043, src2dst_packets=9, src2dst_bytes=1345, dst2src_first_seen_ms=1472393122668, dst2src_last_seen_ms=1472393123665, dst2src_duration_ms=997, dst2src_packets=10, dst2src_bytes=4400, application_name='TLS.Facebook', ...)
```

The README example runs with `statistical_analysis=False`, so it does not show the flag counters. The API reference documents them: `src2dst_syn_packets`, "Flow src2dst syn packet accumulators", and the same for ack, fin, rst, psh, urg, ece and cwr.

Cowrie: **no literal SSH login or command log line found in the Cowrie 3.1.0 documentation.** `docs/OUTPUT.rst` documents each event's attributes. `docs/EVENT_PIPELINE.rst` documents the message format of command input, `"CMD: %(input)s"`, and the only literal JSON in the documentation is a VirusTotal event (`docs/virustotal/README.rst`). See Consequences.

Licences. Cowrie: BSD-3-Clause (`LICENSE.rst`, SPDX header). NFStream: LGPL-3.0 (GitHub licence detection). NFStream runs in its own container and is not linked into `thesis`, so LGPL places no obligation on the `thesis` code.

## Alternatives considered

Honeypot:

| Option | For | Against |
|---|---|---|
| **Cowrie 3.1.0** (BSD-3-Clause) | Meets C2: `cowrie.login.failed` / `cowrie.login.success` carry username and password, and `cowrie.command.input` carries each typed line; JSON output; official Docker image; active (3.1.0 released 2026-10-02) | Larger than a single binary (Python and Twisted); 3.1.0 is two days old at the time of writing |
| sshesame 0.0.39 (Apache-2.0) | Single Go binary; arm64 images published; JSON activity log | "Lets anyone in", so every password succeeds and success / fail carries no signal; last release 2024-08-03, outside C5 |
| Kippo 0.9 (no licence detected by GitHub) | Cowrie's predecessor | Last release 2014-05-27; superseded by Cowrie; fails C5 |

Flow exporter:

| Option | For | Against |
|---|---|---|
| **NFStream 6.6.0** (LGPL-3.0) | Meets C3 directly: `dst_ip`, `dst_port`, `protocol`, `src2dst_bytes` / `dst2src_bytes`, per-flag packet counters, `bidirectional_duration_ms`; reads live interfaces and pcap files; Python records, no text parsing; manylinux aarch64 wheels | Flag counters need `statistical_analysis=True`, and with it off they are absent with no error |
| Argus 5.0.4 and clients 5.0.4 (GPL-3.0) | Mature flow auditor; per-flow state and TCP flag indicators; Dockerfile in the repository | Two components (the `argus` daemon plus `ra` clients to read its binary records); the flags come as a fixed-width indicator string that has to be decoded |
| Zeek 9.0.0 (BSD-style, `COPYING`) | `conn.log` gives `id.resp_h`, `id.resp_p`, `proto`, `duration`, `orig_bytes` / `resp_bytes`, `conn_state` and `history`; official arm64 image | A full network-analysis framework, which is close to the "packet-analytics tools" in the ticket's Scope Out; TCP flags come only through the `history` letter string, so the SYN-only ratio would be derived from `history` or `conn_state` instead of a counter; largest footprint of the three |

Screened out before the shortlist: softflowd 1.1.1 with nfdump 1.7.10 (two components, NetFlow export plus a collector) and CICFlowMeter (no GitHub release; last push 2023-12-04).

Memory (C1): none of the projects publishes a memory figure for a small testbed. E0-07 measures the two chosen containers with `docker stats` under benign load.

## Consequences

- E0-07 adds a Cowrie 3.1.0 container and NFStream 6.6.0 inside the capture sidecar. Whether NFStream reads the sidecar interface live or reads pcap files written by a capture tool is E0-07's choice. A separate capture tool (for example tcpdump) needs this ADR amended or a new one.
- E0-07 pins `statistical_analysis=True` and `accounting_mode` in the sidecar config, and checks that `src2dst_syn_packets` is present on a test flow. Without it the SYN-only ratio is silently missing (ticket risk).
- E0-07 checks on a test pcap that NFStream's `src_ip` is the sender of a flow's first packet. The SYN-only formula assumes it. The API page documents packet direction but does not state this rule.
- The flow parser (E3) maps `NFlow` to `FlowDetail`. `FlowDetail.tcp_flags` is a string in alert-v0.1, while NFStream emits per-flag counts. The SYN-only formula needs `src2dst_syn_packets` and `src2dst_ack_packets` to survive normalization, so E0-05 and the parser ticket must keep them.
- The honeypot parser (E3) maps Cowrie `session` to `HoneypotDetail.session_id` and `input` to `command`.
- Cowrie listens for SSH only. Telnet stays disabled, since no attack family in record §3.2 uses it.
- Acceptance criterion 3 asks for a Cowrie sample line from its documentation. None exists for login or command events (see Decision). Roy accepted the attribute lists in `docs/OUTPUT.rst` as the substitute (2026-10-04).
- Ruled out: Zeek, Argus, softflowd + nfdump, CICFlowMeter, sshesame, Kippo, and any second honeypot.
