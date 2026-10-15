"""Tests for flow features / the training table (E4-01, SCRUM-23).

Pure-logic tests always run; the corpus-dependent determinism and leakage checks skip when the
frozen corpus is not on disk (it is git-ignored, so CI has no copy).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pyarrow as pa
import pytest

from thesis.detect import flow_features as ff
from thesis.schema.alert import FlowDetail


def _detail(**kw: object) -> FlowDetail:
    base = dict(
        flow_start=datetime(2026, 1, 1, tzinfo=UTC),
        duration_s=5.0,
        src_ip="a",
        src_port=1,
        dst_ip="b",
        dst_port=22,
        protocol="tcp",
        packets_fwd=10,
        packets_bwd=0,
        bytes_fwd=600,
        bytes_bwd=0,
        syn_count_fwd=10,
        ack_count_fwd=0,
    )
    base.update(kw)
    return FlowDetail(**base)  # type: ignore[arg-type]


def test_features_describe_behaviour_not_addresses() -> None:
    feats = ff.flow_features(_detail())
    assert set(feats) == set(ff.FEATURES)
    assert not ({"src_ip", "dst_ip", "src_port"} & set(feats))  # no raw addresses


def test_syn_only_probe_values() -> None:
    feats = ff.flow_features(
        _detail(packets_fwd=10, packets_bwd=0, syn_count_fwd=10, ack_count_fwd=0)
    )
    assert feats["syn_ratio_fwd"] == 1.0  # SYN per initiator packet
    assert feats["is_tcp"] == 1.0 and feats["is_udp"] == 0.0
    assert feats["fwd_bwd_packet_ratio"] == 10.0  # one-sided


def test_bytes_per_packet_and_udp() -> None:
    feats = ff.flow_features(
        _detail(protocol="udp", packets_fwd=2, packets_bwd=2, bytes_fwd=80, bytes_bwd=120)
    )
    assert feats["bytes_per_packet"] == 50.0 and feats["is_udp"] == 1.0 and feats["is_tcp"] == 0.0


def test_leakage_check_flags_eval_episode() -> None:
    table = pa.table({"episode_id": ["ep-train-1", "ep-eval-9", ""]})
    assert ff.leakage_check(table, {"ep-eval-9"}) == ["ep-eval-9"]
    assert ff.leakage_check(table, {"ep-eval-123"}) == []


@pytest.mark.skipif(not any(ff.CORPUS_DIR.glob("*/")), reason="frozen corpus not on disk")
def test_training_table_is_deterministic_and_leak_free(tmp_path) -> None:  # type: ignore[no-untyped-def]
    a = ff.build_training_table(tmp_path / "a.parquet")
    ff.build_training_table(tmp_path / "b.parquet")
    assert (tmp_path / "a.parquet").read_bytes() == (tmp_path / "b.parquet").read_bytes()
    assert ff.leakage_check(a, ff.evaluation_episode_ids()) == []
    assert a.num_rows > 0
