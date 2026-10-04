<!-- METHODS.md v1.0, Annex E. Moved verbatim from METHODS.md by SCRUM-24 [E0-03]. The text below the next line is frozen and unchanged (source: `reduction-v1.0`). -->

## Reduction policy v1.0

Ticket SCRUM-44 [E0-05]. Decided by Roy El Hayek, 2026-10-04, who adopted the options suggested in the ticket's decision brief. Frozen at git tag `reduction-v1.0`. Settles conflict C-02 (the input token budget). Traces to record §4, §4.1 and §4.4, and to H1 and H4.

Inputs: alert schema v0.1 (`thesis/schema/alert.py`, `alert-v0.1`); ADR-0002 (Cowrie 3.1.0, NFStream 6.6.0, with its field mapping); record §3.3, §4, §4.1, §4.4, §4.4.1 and §6.3–§6.6; the E0-01 spike bundle (`spikes/bundle_ssh_bruteforce.json`) and `spikes/FINDINGS.md`; action catalog v0.1 (`knowledge/action_catalog.yaml`, tag `catalog-v0.1`). The worked example is `docs/reduction_worked_example.md`.

### 1. Principle

The **reduced view** is the only representation of a bundle that any condition receives: every agentic condition, Baseline A and Baseline B (record §4.1, §4.4 rule 1). It is computed deterministically from the bundle's alerts, outside the agent, before any condition runs. No condition reads raw alerts. Rationale: if the agent saw a reduced view and a baseline the full one, H4 would be contaminated (record §4.1).

Every condition receives raw-flow information in one way only: through the detector scores and labels in the view (§7). This holds for all conditions alike.

Device context (role, criticality) and retrieved knowledge are not part of the reduced view. They are added per condition by the graph (record §6.3) and are outside this policy.

### 2. Structure

The view is one JSON object. Its keys appear in this order:

| Key | Content |
|---|---|
| `bundle_id` | The bundle's ID |
| `window` | `[start, end]` of window W, ISO 8601 UTC |
| `device` | The subject device D (record §4.1) |
| `sources` | The state of each source, always all three in the order `flows`, `mqtt`, `honeypot`: `active`, `no_alerts` or `not_in_config` (alert-v0.1 `SourceState`) |
| `flows`, `mqtt`, `honeypot` | One block per source whose state is `active`, in that order. There is no block for `no_alerts` or `not_in_config`; the state in `sources` carries that information |

Within a source block the keys appear in this order: the aggregates (§3, in table order), `detector` (§7), the exemplars (§4), then `other_ids` (§5).

### 3. Aggregates

Notation: `A_s` is the set of the bundle's alerts from source `s`. Field names are those of alert-v0.1, with the emitting tool's field in brackets. `addr(D)` is the set of IP addresses the device table assigns to D (`thesis/schema/devices.py`). "Out" means sent by D. Unless stated otherwise, `min`, `median` and `max` are taken over the values present; the median of an even number of values is the mean of the two middle values.

**Flows** (ADR-0002 mapping)

| Key | Formula |
|---|---|
| `count` | `|A_flows|` |
| `unique_dst_ips` | number of distinct `dst_ip` |
| `unique_dst_ports` | number of distinct `dst_port` |
| `bytes_out` | Σ `bytes_fwd` [`src2dst_bytes`] over flows with `src_ip ∈ addr(D)`, plus Σ `bytes_bwd` [`dst2src_bytes`] over flows with `dst_ip ∈ addr(D)` |
| `bytes_in` | Σ `bytes_bwd` over flows with `src_ip ∈ addr(D)`, plus Σ `bytes_fwd` over flows with `dst_ip ∈ addr(D)` |
| `protocol_mix` | number of flows per `protocol`, keyed by lowercase protocol name (`tcp`, `udp`, `icmp`, …), keys ordered by count descending, then name ascending |
| `syn_only_ratio` | flows with `protocol = tcp`, initiator SYN count [`src2dst_syn_packets`] ≥ 1 and initiator ACK count [`src2dst_ack_packets`] = 0, divided by flows with `protocol = tcp`. Omitted when there is no TCP flow |
| `duration_s` | `{min, median, max}` of `duration_s` [`bidirectional_duration_ms` / 1000] |

A flow with neither address in `addr(D)` counts toward every key except `bytes_out` and `bytes_in`.

**MQTT**

| Key | Formula |
|---|---|
| `message_count` | number of alerts with `event = publish` |
| `unique_topics` | number of distinct `topic` over `publish` alerts |
| `payload_bytes` | `{min, median, max}` of `payload_bytes` over `publish` alerts. Omitted when there is none |
| `qos_mix` | number of `publish` alerts per `qos`, keyed by QoS level, keys ascending |
| `connect_count` | number of alerts with `event = connect` |
| `disconnect_count` | number of alerts with `event = disconnect` |
| `auth_failures` | number of alerts with `event = auth_failure` |

**Honeypot** (ADR-0002 mapping; Cowrie event in brackets)

| Key | Formula |
|---|---|
| `session_count` | number of distinct `session_id` over `session_connect` alerts [`cowrie.session.connect`] |
| `unique_src_ips` | number of distinct `src_ip` over all honeypot alerts |
| `auth_attempts` | `login_failed` + `login_success` |
| `login_success` | number of alerts with `event = login_success` [`cowrie.login.success`] |
| `login_failed` | number of alerts with `event = login_failed` [`cowrie.login.failed`] |

Rationale: the fields are exactly those of record §4.4; the duration and payload statistics are min, median and max because they resist outliers and cost three numbers.

### 4. Exemplars

| Source | Count | Ranking key | Tie-break |
|---|---|---|---|
| Flows | at most 5 | the flow detector's alert score, descending | earlier `ts` first, then `alert_id` ascending |
| MQTT | at most 3 | the MQTT detector's alert score, descending | earlier `ts` first, then `alert_id` ascending |
| Honeypot | at most 3 command sequences, one per session with at least one command line | number of command lines, descending | earlier first command line first, then `session_id` ascending |

An alert without a score ranks after every alert with one. If no alert of a source has a score, the ranking falls back to the tie-break alone. Rationale: the counts and ranking keys are those of record §4.4. Honeypot sequences are ranked by command lines rather than a detector score so that the rule does not depend on EPIC-4 (C-15); the sequence with the most commands shows the most attacker behaviour.

**Exemplar fields.** Absent optional fields are left out.

- Flow: `id` (`alert_id`), `t`, `src` (`src_ip:src_port`), `dst` (`dst_ip:dst_port`), `proto`, `dur_s`, `bytes_fwd`, `bytes_bwd`, `pkts_fwd`, `pkts_bwd`, `flags` (`tcp_flags`), `score`.
- MQTT: `id`, `t`, `event`, `client` (`client_id`), `topic`, `qos`, `payload_bytes`, `score`.
- Honeypot sequence: `id` (the `alert_id` of the session's first command line), `session` (`session_id`), `src` (`src_ip:src_port` of the session's `session_connect` alert, or `src_ip` alone when the port is unknown), `cmd` (§6).

`t` is the alert's time in seconds since the start of W. `src` and `dst` keep the address and port that tie a flow to a honeypot session (FINDINGS.md, gap 2).

### 5. Other alert IDs

Each source block carries `other_ids`: at most **5** alert IDs of that source that are not already shown as an exemplar `id`. Flows and MQTT use the exemplar ranking of §4. The honeypot orders its alerts by event class first: command lines [`cowrie.command.input`, `cowrie.command.failed`], then `login_success`, then `login_failed`, then all other events. Within a class the order is earlier `ts` first, then `alert_id` ascending. The key is left out when it is empty.

Rationale: the output's `evidence` is a list of alert IDs from the input, and the validator rejects any other ID (record §6.4, §6.5). Without `other_ids`, a source reduced to aggregates gives the model nothing to cite. On the spike bundle, no honeypot alert could be cited, although both spike models cited only honeypot alerts (FINDINGS.md). Cross-source evidence must stay visible for H1. Five IDs per source cost about 25 tokens.

### 6. Honeypot command sequences: cap and delimiter

- **Content.** The `input` of every command-line alert of the session [`cowrie.command.input` without a `realm` attribute, and `cowrie.command.failed`], in `ts` order (ADR-0002).
- **Cleaning.** Every control character (U+0000–U+001F and U+007F) in a command line is replaced by one space.
- **Delimiter.** The command lines are joined with ` ; ` (space, semicolon, space). The whole sequence is the JSON string value of `cmd`. JSON string escaping is the delimiter: no attacker text can close the string or add a key.
- **Cap: 200 characters** (Unicode code points) of the joined sequence. A longer sequence is cut at 200 and followed by `…[+K chars]`, where K is the number of characters removed. Truncation happens after joining, so one long command line cannot push the others out unseen; the marker shows that something was cut.

Rationale: honeypot text is an injection channel, and record §3.3 requires strict delimiting and hard truncation. 200 characters keep the start of a typical dropper one-liner (download, `chmod`, execute), about 87 tokens on the synthetic worst case. Placing the block in the prompt (never next to schema instructions, record §3.3) is a prompt-template matter, not part of this policy.

### 7. Detector fields

Each source block carries `detector`: `max_score`, the highest alert score of that source's detector over the source's alerts, and `label`, the detector's label for the top-ranked alert (§4; for the honeypot, the highest-scored alert). A key is left out when the detector gives no value. What the score and label mean is defined by the detector tickets (EPIC-4, C-15), not here.

### 8. Serialization

- Compact JSON: separators `,` and `:`, no whitespace, UTF-8 characters written as they are (not `\u` escapes). Keys appear in the order given above.
- Rounding: scores and ratios to 2 decimals; seconds (`t`, `dur_s`, duration statistics) to 3 decimals; bytes and counts as integers.
- Empty lists and absent values are left out. A count of 0 is written.

### 9. Token budget (C-02)

| | Target | Hard ceiling |
|---|---|---|
| Input tokens per LLM call | 2,000 | 2,500 |
| Output tokens per LLM call | 200 | 250 |

The ceilings apply to every LLM call, agentic and Baseline B, and are asserted in code (E3-08). A call whose prompt would exceed the input ceiling is a reduction or prompt failure, found at build time.

**Side of C-02 chosen: record §4 and §4.4 (2,000 / 2,500), not the ~3,000-token figure of §4.4.1.** Why: the measurements leave room inside the ceiling, and this side keeps the locked §4 row unchanged. Measured with the Llama 3 tokenizer: the reduced view is 486 tokens on the spike bundle, and at most 1,324 tokens on a synthetic view with every cap full (5 flow exemplars, 3 MQTT exemplars, 3 command sequences at 200 characters, 5 `other_ids` per source). The action catalog, given as ID and description, is 166 tokens. The largest calls, evidence analysis (node 1) and Baseline B, are estimated at 1,800–2,200 tokens with a full view, below the ceiling. §4.4.1's ~3,000 tokens is kept as a cost estimate only. It overstates the input, so the cost budget it supports remains conservative.

Record §4.4 estimates that a reduced view "lands around 800–1,200 tokens". The spike view (486) is below that range because the bundle is small. The synthetic worst case (1,324) is about 10 % above it. The range is an estimate, not a limit: the binding limits are the per-call ceilings above.

Accepted risk: node 1's output ("findings per source and cross-source observations", record §6.3) is free text and may hit the 250-token ceiling. E3-08's token report will show it. Any change goes through a changelog entry.

### 10. Reduction ratio

The **reduction ratio** is the token count of the bundle as compact JSON (its header and alerts, without ground truth, serialized as in §8) divided by the token count of its reduced view. On the spike bundle: 1,351 ÷ 486 = **2.78**. Against the bundle exactly as the spike sent it (indented JSON, 1,892 tokens), the ratio is 3.89. That figure is reported for reference only, because it is inflated by whitespace.

Tokenizer: Llama 3 (vocabulary of 128,256 tokens), taken from the local development model (`llama3.1-8b-8k`, Llama 3.1 8B Q4_K_M, Ollama digest 6811dcd559d9). The counts were made through Ollama and checked against the same tokenizer loaded directly from the model file: identical on six texts.

The spike bundle holds 13 alerts, no MQTT alerts and no command lines, so 2.78 **understates the ratio on busy windows**. The reduced view is bounded (1,324 tokens at most on the synthetic worst case), while the raw bundle grows by about 104 tokens per alert, so the ratio grows roughly in proportion to the alert count. The ratio over the pilot bundles is reported by E3-08; it does not replace this frozen figure.

### 11. Baseline A's input view

Baseline A is the flow classifier itself: one artifact that serves as both the flow detector and the baseline (record §4, §5, §6.2; E4-03). Like every condition, it receives only the reduced view (§1). Its per-flow scoring is the shared step that fills the `flows` block's exemplar `score`, `detector.max_score` and `detector.label` (§4, §7), and every condition receives that output alike. Baseline A's verdict for a bundle is read from the reduced view and nothing else. Its predicted class is `detector.label` of the `flows` block, which is the flow classifier's label for its top-ranked flow. When the bundle has no `flows` block (flows `no_alerts` or `not_in_config`), it predicts `benign`. The severity→action lookup (E8-01) maps that verdict to an action. Baseline A reads no other key of the view: no `other_ids`, no MQTT or honeypot block and no command text. Rationale: this keeps Baseline A's view identical to the agent's (record §4.1) and keeps it the artifact the record locks. The cost is that Baseline A uses flow evidence only, which is what it is there to measure: "Do we need an LLM at all?" (record §6.6). The label set comes from EPIC-4, what the classifier trains on is decided by E2-01, and its freeze is E4-03.

### 12. ASSUMPTIONs and dependencies

- **ASSUMPTION 1. Tokenizer.** The experiment model is not yet pinned (E0-06 depends on this ticket). The counts use the Llama 3 tokenizer of the spike's model family. Llama 3.3 is assumed to share it (UNVERIFIED). If E0-06 pins a model with a different tokenizer, §9 and §10 are re-measured through a changelog entry.
- **ASSUMPTION 2. MQTT event names.** `publish`, `connect`, `disconnect` and `auth_failure` are placeholders until alert schema v1 (E3-01) fixes the vocabulary. The renaming goes through a changelog entry; the formulas do not change.
- **ASSUMPTION 3. `other_ids` (§5).** Neither the ticket nor the record names this mechanism. It is added so that sources reduced to aggregates keep citable evidence (record §6.4, §6.5; H1).
- **ASSUMPTION 4. Baseline A without flows (§11).** When a bundle has no `flows` block, Baseline A predicts `benign`. The record does not cover this case.
- **Dependency, E3-01.** alert-v0.1 `FlowDetail` has a `tcp_flags` string but no SYN or ACK counters. `syn_only_ratio` needs `src2dst_syn_packets` and `src2dst_ack_packets`, so v1 must carry them (ADR-0002). In the worked example the ratio is derived by hand from `tcp_flags`.
- **Dependency, EPIC-4 (C-15).** Exemplar ranking and `detector` use detector scores and labels that do not exist yet. In the worked example, the flow scores are the spike bundle's hand-written `anomaly_score` values.
- **Dependency, E3.** Every token count assumes short alert IDs such as `fl-0003`. Longer IDs would raise the view's size.

### 13. Options considered

| Question | Chosen | Rejected |
|---|---|---|
| Input budget (C-02) | 2,000 target / 2,500 ceiling (record §4, §4.4) | 3,000 / 3,500 (§4.4.1; changes a locked row without a measured need); 2,000 target with a 3,000 ceiling (headroom not needed on the measured sizes) |
| Baseline A's view | The flow classifier itself (record §4, §5), its verdict read from `flows.detector.label`, `benign` when there is no `flows` block | A separate bundle-level classifier over every aggregate (a second model; contradicts record §5, "one artifact, two purposes", and E4-03); raw flows (violates record §4.1, contaminates H4) |
| Honeypot cap | 200 characters | 128 (cuts most dropper commands mid-URL; saves 84 tokens at the worst case); 256 (+75 tokens at the worst case) |
| Honeypot sequence ranking | Most command lines | Chronological (the first sessions may be idle); detector score (depends on EPIC-4) |
| Duration and payload statistics | min, median, max | mean and standard deviation (sensitive to outliers); median, p95, max (p95 is unstable on small windows) |
| Citable IDs for aggregated alerts | Up to 5 `other_ids` per source | Exemplar IDs only (hides cross-source evidence, H1); a pseudo-ID per source (changes the output schema and validator of record §6.4, §6.5) |
| Raw text for the ratio | Compact JSON | The spike's indented JSON (whitespace inflates the ratio) |
| Inactive sources | State in `sources`, no block | Zero-filled block (40–80 tokens; the state already says it) |
