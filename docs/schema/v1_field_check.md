# Alert schema v1 field check (E3-01, SCRUM-21)

One real line per source from the frozen corpus (`data/raw/corpus-v1.0.0/`) is mapped by hand into
`Alert` (`thesis/schema/alert.py`, `alert-v1`), and every field named by the frozen reduction
policy (Annex E, `reduction-v1.0`) is shown populated or derivable. This closes AC 1 of E3-01.

The device mapping (`subject_device`, §4.1) is unchanged; only `Alert` fields are checked here.

## Flows — NFStream record → `FlowDetail`

Raw (one `flows/flows.jsonl` record, abridged): `src_ip 10.77.0.30, dst_ip 10.77.0.10,
src_port …, dst_port 22, protocol 6, bidirectional_duration_ms, src2dst_packets, dst2src_packets,
src2dst_bytes, dst2src_bytes, src2dst_syn_packets 1, src2dst_ack_packets 0`.

| Reduction field (Annex E §3/§4/§7) | Source in `Alert` | Status |
|---|---|---|
| `count`, `unique_dst_ips`, `unique_dst_ports` | aggregated over `dst_ip`, `dst_port` | derivable |
| `bytes_out`, `bytes_in` | `bytes_fwd` [`src2dst_bytes`], `bytes_bwd` [`dst2src_bytes`] with `addr(D)` | populated |
| `protocol_mix` | `protocol` (normalizer maps `6`→`tcp`, E3-03) | populated |
| **`syn_only_ratio`** | **`syn_count_fwd` [`src2dst_syn_packets`], `ack_count_fwd` [`src2dst_ack_packets`]** | **populated (new in v1)** |
| `duration_s {min,median,max}` | `duration_s` [`bidirectional_duration_ms`/1000] | populated |
| exemplar `src/dst/proto/dur_s/bytes_fwd/bytes_bwd/pkts_fwd/pkts_bwd/flags` | `src_ip:src_port`, `dst_ip:dst_port`, `protocol`, `duration_s`, `bytes_*`, `packets_*`, `tcp_flags` | populated |
| exemplar `score`, detector `max_score`/`label` | `detector_score`, `detector_label` | present (new in v1; written by EPIC-4) |

v0.1 gap closed: it had only `tcp_flags` (a flag string), which cannot give the initiator SYN/ACK
counts `syn_only_ratio` needs. v1 adds `syn_count_fwd`/`ack_count_fwd`.

## MQTT — subscriber log + broker log → `MqttDetail`

Raw: a `mqtt/mqtt.log` publish line `2026-10-11T… iot/iot-temp-01/flood {…}` (topic + payload, no
client id or addresses), and a `mqtt/broker.log` line `… Client iot-temp-01-brute disconnected,
not authorised.` for auth failures.

| Reduction field | Source in `Alert` | Status |
|---|---|---|
| `message_count` | alerts with `event = publish` | derivable |
| `unique_topics` | `topic` over publishes | populated |
| `payload_bytes {min,median,max}` | `payload_bytes` (length of the publish payload) | populated |
| `qos_mix` | `qos` (when the log carries it; optional) | derivable |
| `connect_count`, `disconnect_count`, `auth_failures` | `event` ∈ {`connect`,`disconnect`,`auth_failure`} from the broker log | derivable |
| exemplar `event/client/topic/qos/payload_bytes/score` | `event`, `client_id`, `topic`, `qos`, `payload_bytes`, `detector_score` | populated / optional |

v0.1 gap closed: it required `client_id`, `src_ip`, `dst_ip`. A publish seen on the subscriber log
has none, so v1 makes them optional; the subject device is mapped from the topic, not these
fields.

## Honeypot — Cowrie event → `HoneypotDetail`

Raw: a `honeypot/cowrie.json` event `{"eventid":"cowrie.session.connect","session":"…",
"src_ip":"10.77.0.30","src_port":…,"dst_ip":"10.77.0.10","dst_port":22,"timestamp":"…Z"}`, and
`cowrie.login.failed` / `cowrie.command.input` events.

| Reduction field | Source in `Alert` | Status |
|---|---|---|
| `session_count` | distinct `session_id` over `session_connect` | derivable |
| `unique_src_ips` | `src_ip` | populated |
| `auth_attempts`, `login_success`, `login_failed` | `event` ∈ {`login_success`,`login_failed`} | derivable |
| exemplar command sequence `cmd` | `command` over the session's command-line events | populated |
| exemplar `id`, `session`, `src` | `alert_id`, `session_id`, `src_ip:src_port` | populated |

No v0.1 gap: the honeypot detail already carried `session_id`, `src_ip/src_port`, `event` and
`command`. Honeypot exemplars rank by command-line count, not a detector score (Annex E §4), so
the honeypot does not depend on EPIC-4.

## Conclusion

Every field the reduction policy names is populated or derivable from `alert-v1`. The three v1
changes — `syn_count_fwd`/`ack_count_fwd` on flows, optional `client_id`/`src_ip`/`dst_ip` on MQTT,
and `detector_score`/`detector_label` on the envelope — are the only changes from v0.1
(`docs/schema/CHANGELOG.md`).
