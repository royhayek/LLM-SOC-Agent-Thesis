# Flow features (E4-01, SCRUM-23)

Per-flow features for the flow classifier / Baseline A, computed by thesis/detect/flow_features.py.
Behaviour only - no raw IP addresses, so the classifier cannot memorise the attacker or the
testbed addresses (record §6.6). The training table (data/features/flows_train.parquet) is built
from benign windows and training-split attack episodes only (E2-01); evaluation episodes are
excluded and a leakage check enforces it.

| Feature | Reason |
|---|---|
| `duration_s` | flow lifetime; scans are near-instant, floods and sessions last longer |
| `packets_fwd` | initiator packet count; floods and scans are initiator-heavy |
| `packets_bwd` | responder packet count; a refused/absent service answers little |
| `bytes_fwd` | initiator bytes; separates chatty sessions from probes |
| `bytes_bwd` | responder bytes |
| `total_packets` | overall volume of the flow |
| `total_bytes` | overall size of the flow |
| `bytes_per_packet` | mean packet size; floods use tiny packets, transfers large ones |
| `fwd_bwd_packet_ratio` | directionality; one-sided for scans and SYN floods |
| `syn_count_fwd` | initiator SYNs; high for scans and SYN floods |
| `ack_count_fwd` | initiator ACKs; near-zero when no handshake completes |
| `syn_ratio_fwd` | SYNs per initiator packet; ~1 for SYN-only probes |
| `dst_port` | destination service port (behaviour, not an address): 22/80/1883 differ by attack |
| `is_tcp` | transport is TCP |
| `is_udp` | transport is UDP |
| `is_icmp` | transport is ICMP |

Target column: `label` (the six families or `benign`). `episode_id` is kept for episode-grouped
cross-validation (E4-02) and the leakage check; `device` for inspection. Neither is a model input.
