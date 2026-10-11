"""Split the corpus schedule into independent chunks for the generation run (E2-05, SCRUM-52).

The corpus is ~4.6 h of wall-clock (docs/corpus/expected_counts.md). Running it as one capture
risks losing everything on a single failure and a large transient pcap. The schedule ASSUMPTION
(E2-05) allows splitting it into chunks, each run from `make reset` with its own run id; the
corpus is the union of the chunks.

Each chunk is an independent, valid `Schedule`: the same episodes (by id, family, device,
duration, seed, split) and benign blocks as the master schedule, re-laid-out per device from
offset 0 so the chunk is short. Ground truth comes from each chunk's *executed* times (E2-04), so
the rebased offsets do not matter. `chunk_schedule` guarantees every episode and benign block
appears in exactly one chunk (asserted), so chunking can never drop or duplicate corpus items.
"""

from __future__ import annotations

from collections import defaultdict

from thesis.scenario.schedule import BenignPeriod, Episode, Schedule

GAP_S = 60  # idle gap between consecutive episodes on one device, as in the generator


def _relayout(episodes: list[Episode], benign: list[BenignPeriod]) -> Schedule:
    """Re-place a chunk's items on a fresh timeline: each device's episodes back to back from 0
    with a gap, then the benign blocks after the last episode. Preserves every other field."""
    next_start: dict[str, int] = defaultdict(int)
    placed: list[Episode] = []
    for ep in sorted(episodes, key=lambda e: (e.target_device, e.id)):
        start = next_start[ep.target_device]
        next_start[ep.target_device] = start + ep.duration_s + GAP_S
        placed.append(ep.model_copy(update={"start_offset_s": start}))

    attack_end = max((e.end_offset_s for e in placed), default=0)
    placed_benign: list[BenignPeriod] = []
    offset = attack_end
    for b in sorted(benign, key=lambda x: x.id):
        placed_benign.append(b.model_copy(update={"start_offset_s": offset}))
        offset += b.duration_s
    return Schedule(episodes=tuple(placed), benign_periods=tuple(placed_benign))


def chunk_schedule(schedule: Schedule, n_chunks: int) -> list[Schedule]:
    """Partition the schedule into `n_chunks` independent sub-schedules.

    Each device's episodes are spread round-robin across the chunks, so the busiest device (the
    honeypot) is balanced and no chunk is much longer than the others. Benign blocks are spread
    the same way. Every episode and benign block lands in exactly one chunk.
    """
    if n_chunks < 1:
        raise ValueError("n_chunks must be at least 1")

    ep_buckets: list[list[Episode]] = [[] for _ in range(n_chunks)]
    by_device: dict[str, list[Episode]] = defaultdict(list)
    for ep in schedule.episodes:
        by_device[ep.target_device].append(ep)
    for device in sorted(by_device):
        for i, ep in enumerate(sorted(by_device[device], key=lambda e: e.id)):
            ep_buckets[i % n_chunks].append(ep)

    bn_buckets: list[list[BenignPeriod]] = [[] for _ in range(n_chunks)]
    for i, b in enumerate(sorted(schedule.benign_periods, key=lambda x: x.id)):
        bn_buckets[i % n_chunks].append(b)

    chunks = [_relayout(ep_buckets[i], bn_buckets[i]) for i in range(n_chunks)]

    # Safety: chunking must never drop or duplicate a corpus item (the corpus is the instrument).
    chunked_ep_ids = sorted(e.id for c in chunks for e in c.episodes)
    assert chunked_ep_ids == sorted(e.id for e in schedule.episodes), "episodes lost in chunking"
    chunked_bn_ids = sorted(b.id for c in chunks for b in c.benign_periods)
    master_bn_ids = sorted(b.id for b in schedule.benign_periods)
    assert chunked_bn_ids == master_bn_ids, "benign lost in chunking"
    return chunks
