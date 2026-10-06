# ADR-0009: Whole-network flow capture with per-host egress sidecars

- Status: Proposed
- Date: 2026-10-06
- Ticket: SCRUM-129 [E1-16]

## Context

ADR-0003 (E1-04) decided that the flow source observes all traffic on the testbed network,
not the broker's namespace alone, so that the frozen visibility matrix (`families-v1.0`,
METHODS.md Changelog entry 1) holds: every family predicts flows. It left the mechanism to
"an ADR-0008 amendment before any attack traffic is captured". This is that ADR. It changes
only where packets are captured; tcpdump, the pcap as raw telemetry and NFStream reading the
pcap offline (ADR-0008, ADR-0002) stay.

Today one tcpdump runs in the broker's network namespace (`-i eth0`, ADR-0008; METHODS.md
Annex F ASSUMPTION 3). It sees every connection to or from the broker and nothing else, so
`ssh_brute_force` and `port_scan` (attacker to honeypot), `syn_flood` (attacker to a device)
and `botnet` (a device to an external address) would leave no flow.

Requirements (E1-16):

1. **Complete.** Every packet a testbed host sends is captured.
2. **Once.** No packet appears twice; duplicates would double flow packet and byte counts.
3. **Both directions in one file.** NFStream builds bidirectional flows (`src2dst_*`,
   `dst2src_*`, ADR-0002) from one input, so the two directions of a connection must end up
   in the same pcap.
4. **One clock.** All timestamps come from one clock (E1-07's rule; record §4.1).
5. **Isolation intact.** No capture container may sit in the Docker host's network
   namespace; the egress check (E0-07, E1-01) must still pass.
6. **No new hand-written capture code** (ADR-0008 rejected it).

On a Linux bridge a container's interface receives only frames addressed to it, so no single
container on the testbed network can observe the others' unicast traffic.

## Decision

Proposed: option A below. Roy accepts or changes it.

- **One capture sidecar per testbed host that sends traffic.** Each runs the existing capture
  image in that host's network namespace (`network_mode: service:<host>`, as the broker's
  sidecar does today) and records only the packets the host sends:
  `tcpdump -i eth0 -Q out -s 0 -n -U -w /out/<host>.pcap`. A packet is therefore captured
  exactly once, at its sender, whichever host receives it. Hosts: broker, mqtt-logger,
  honeypot, the four emulators. The attacker container (added by the first family ticket
  that needs it) gets its own sidecar the same way.
- **Merge at `make down`.** After the traffic sources and the sidecars stop, `tcpslice`
  merges the per-host pcaps in timestamp order into `flows/raw.pcap`; NFStream then reads
  `raw.pcap` exactly as in ADR-0008. The per-host pcaps stay in `flows/hosts/` as raw
  telemetry, so the merge can be re-run. tcpslice 1.5 stops on a pcap with no packet (only
  its 24-byte header, left by a host that sent nothing), so `testbed/capture/merge.sh` merges
  only the pcaps that hold a packet, and copies a header-only pcap when every host was silent.
- **tcpslice 1.5** (Debian bookworm package `tcpslice` 1.5-1), from the tcpdump project,
  added to the capture image next to tcpdump 4.99.3-1. Licence: BSD-style (UNVERIFIED, not
  checked against the project's licence file). Not linked into the `thesis` package.
- **Start-up grace.** A sidecar can only join its host's namespace once the host runs, so a
  host that opens connections at start-up waits 5 s first (the emulators and the MQTT logger);
  otherwise its opening packets are lost and NFStream records the flow reversed.
- **One clock.** Every container shares the Docker VM's kernel, so all sidecars stamp packets
  from the same clock. A packet is stamped as it leaves its sender rather than as it reaches
  the receiver.

Evidence, from a prototype on an isolated internal Docker network (2026-10-06): two hosts
exchanged five TCP connections; each had an egress-only sidecar, and a third sidecar captured
both directions on one host. The merged egress pcap held the same 50 IPv4 packets as the
both-directions capture, in the same order, with no duplicate, and timestamps within 27 µs of
each other. The both-directions capture also held 10 IPv6 link-local packets (multicast
listener reports and neighbour solicitations), mostly sent by the Docker bridge gateway,
which has no sidecar. On an `internal: true` network the gateway routes nothing, so it sends
no testbed flow.

## Alternatives considered

| Option | For | Against |
|---|---|---|
| **A. Egress-only sidecar per host, merged with tcpslice** (proposed) | Every packet once, at its sender; both directions in one merged file; one kernel clock; no host-namespace container, so isolation is untouched; reuses the ADR-0008 image and tool; checked by prototype | One sidecar per host (7 now, 8 with the attacker); a host added without a sidecar silently drops its outbound traffic (mitigated by a test, below); one new small tool (tcpslice) |
| B. A capture container that routes between per-host subnets | One capture point, like a real tap | Rewrites the testbed's addressing into one subnet per host; every host needs a route through the capture container; the router becomes part of the measured path; much larger change |
| C. tcpdump on the Docker host's bridge (`network_mode: host`) | One capture point, no merge | Puts a container in the Docker host's network namespace, which can reach the LAN and the internet: the isolation check would fail (record §6.11) |
| D. Option A merged with `mergecap` (Debian `wireshark-common`) | Widely used merge tool | Pulls about 32 packages into the capture image for one merge step; tcpslice does the same job from the tcpdump project |
| E. Both-directions capture on every host, deduplicated afterwards | No dependence on the sender having a sidecar | Every host-to-host packet is captured twice; deduplication by timestamp and bytes is fragile (the two copies differ by microseconds) and is hand-written processing in the measurement path |

## Consequences

- `docker-compose.yml` replaces the single `capture` service with one sidecar per traffic
  source; `make down` stops them after the sources, merges with tcpslice, then runs NFStream.
  `testbed/capture/Dockerfile` installs tcpslice.
- The flow source now holds honeypot, device-to-device and device-to-external flows. METHODS.md
  Annex F ASSUMPTION 3 (capture on the broker namespace) is superseded by a changelog entry.
- ADR-0008 stands for the tool chain (tcpdump, pcap, offline NFStream); this ADR replaces only
  its capture point (`-i eth0` on the broker's namespace).
- A test checks that every compose service on the testbed network that can send traffic has
  a capture sidecar, so a host added later cannot be missed silently.
- Per-host pcaps and the merged pcap are both kept: raw telemetry roughly doubles on disk.
  Benign MQTT traffic is small; attack families must keep their pcaps within the run folder.
- Ruled out: host-network capture, a routing capture container, deduplicating
  both-directions captures, and mergecap.
