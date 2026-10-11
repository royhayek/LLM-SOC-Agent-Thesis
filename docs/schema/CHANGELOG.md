# Alert schema changelog

The model is `thesis/schema/alert.py`. The device-mapping rule is `thesis/schema/devices.py`.

## alert-v1 — 2026-10-11 (SCRUM-21, E3-01)

Settled on the pilot and corpus captures. Checked field-by-field against the frozen reduction
policy (Annex E) in `docs/schema/v1_field_check.md`: every field the reduction names is populated
or derivable. Done after the corpus freeze (E2-09), so recorded as a METHODS.md changelog entry
(entry 11); the alert schema is a transform over the raw corpus, so this re-derives bundles and
results from the same raw data and does not regenerate the corpus (C-13).

### Field changes from v0.1, with reason

| Field | Change | Reason |
|---|---|---|
| `FlowDetail.syn_count_fwd`, `FlowDetail.ack_count_fwd` | **added** (optional ints) | The reduction's `syn_only_ratio` (Annex E §3) needs the initiator SYN/ACK packet counts [`src2dst_syn_packets`, `src2dst_ack_packets`]. v0.1 had only `tcp_flags` (a flag string), which cannot give them. |
| `MqttDetail.client_id`, `MqttDetail.src_ip`, `MqttDetail.dst_ip` | **made optional** | A publish seen on the broker's subscriber log carries only its topic and payload; no client id or addresses. v0.1 required them, which the real MQTT capture cannot satisfy. The subject device is mapped from the topic. |
| `Alert.detector_score`, `Alert.detector_label` | **added** (optional) | The reduction (Annex E §4, §7) ranks exemplars by the detector's alert score and fills each `detector` block from it. v0.1 deferred where these live; v1 puts them on the envelope (optional), written by the detectors (EPIC-4) and read by the reduction, so v1 is complete for the reduction without EPIC-4 changing the schema. |

No field was removed; source-specific payload fields stay optional (corpus data may show fields the
pilot did not). `protocol` still differs between sources (transport in flows, application in the
honeypot); the flow↔session link uses IP and port only (Annex E §4), so the two need not align.

## alert-v0.1 — 2026-10-04 (SCRUM-82, E0-08)

First draft. It was written after the E0-01 spike (`spikes/FINDINGS.md`), as record §9 requires. It is not frozen; E3-01 settles v1 on the pilot capture.

### Structure

- Every alert has a common envelope: `schema_version`, `alert_id`, `source` (`flows`, `mqtt` or `honeypot`), `ts` (timezone-aware), `subject_device`, and a typed `detail` for its source.
- `detail` is one model per source (`FlowDetail`, `MqttDetail`, `HoneypotDetail`). No untyped payload dict is used. Unknown fields are rejected, and the detail type must match `source`.
- Unset optional fields are omitted when an alert is serialised (`Alert.to_json()`), because every alert costs prompt tokens (FINDINGS.md, recommendation 2: about 145 tokens per alert in indented JSON).

### Added because of a spike finding

| Field or type | Finding in `spikes/FINDINGS.md` |
|---|---|
| `src_ip`, `src_port`, `dst_ip`, `dst_port` and `protocol`, with the same names in `FlowDetail` and `HoneypotDetail` | "Fields the model asked for or invented", gap 2 (links between sources), and recommendation 3. Both models ignored the flow alerts although their source ports matched the honeypot sessions. Shared names let a flow be tied to a session by its tuple. |
| `HoneypotDetail.session_id` | Same finding. All events of one session share it, so the tuple on the `session_connect` event reaches the whole session. |
| `SourceState` (`active`, `no_alerts`, `not_in_config`) | "Source states (input for the alert schema, E0-08)", gap 3 and recommendation 3. This is a bundle-level type. The bundle model that uses it is built in E3-05. |

### Finding deferred to another ticket

- **Device role and criticality** (gap 1 and recommendation 3). These describe a device, not an alert, so they are not fields of `Alert`. The device inventory (E5-01, `knowledge/devices.yaml`) holds them, and the bundle carries them as device context. Criticality is a locked parameter and is not set here.

### Device mapping

`subject_device()` follows record §4.1. The cases §4.1 does not cover are written down as ASSUMPTIONs 1–5 in METHODS.md, "Alert schema v0.1: device mapping (draft)". Cases 4 (external host to infrastructure) and 5 (device to device) are left open for E3-10.

### Not from the spike

- **MQTT fields.** The spike bundle had no MQTT alerts (`no_alerts`), so every `MqttDetail` field is a first guess for E3-01 to check against the pilot capture.
- **Detector score and label.** Neither is in v0.1. The detectors (EPIC-4) and the reduction policy (E0-05) decide where they live.
- **Placeholder IDs and IPs.** The device and infrastructure IDs and IPs in `devices.py` and in the fixtures are placeholders until the testbed and the device inventory (E5-01) exist.
- **`protocol` differs between sources.** It holds the transport protocol in flows (`tcp`) and the application protocol in honeypot events (`ssh`), so it cannot be part of the tuple that links a flow to a session. E3-01 should either align the two or link on IPs and ports only.
