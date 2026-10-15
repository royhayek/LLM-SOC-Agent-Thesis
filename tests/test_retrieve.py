"""Tests for the deterministic retrieval tool (E5-04, SCRUM-51)."""

from __future__ import annotations

import importlib.util

import numpy as np
import pytest

from thesis.kb.retrieve import K, device_context, rank, retrieve

_HAS_ST = importlib.util.find_spec("sentence_transformers") is not None


def _embeddings() -> tuple[np.ndarray, list[str]]:
    # Two identical rows (b, a) to exercise the tie-break; distinct ids, out of id order.
    rows = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    return rows, ["doc-b", "doc-a", "doc-c"]


def test_rank_is_deterministic_over_100_calls() -> None:
    embeddings, doc_ids = _embeddings()
    query = np.array([1.0, 0.0], dtype=np.float32)
    first = rank(query, embeddings, doc_ids, k=3)
    for _ in range(100):
        assert rank(query, embeddings, doc_ids, k=3) == first


def test_equal_similarity_breaks_ties_by_ascending_doc_id() -> None:
    embeddings, doc_ids = _embeddings()
    query = np.array([1.0, 0.0], dtype=np.float32)
    ranked = rank(query, embeddings, doc_ids, k=2)
    assert [d for d, _ in ranked] == ["doc-a", "doc-b"]  # equal score -> lower id first


def test_device_context_returns_the_inventory_entry() -> None:
    ctx = device_context("iot-cam-01")
    assert ctx["role"] == "ip-camera"
    assert ctx["criticality"] == "high"
    assert ctx["id"] == "iot-cam-01"


def test_device_context_unknown_device_raises() -> None:
    with pytest.raises(KeyError):
        device_context("no-such-device")


@pytest.mark.slow
@pytest.mark.skipif(not _HAS_ST, reason="needs sentence-transformers + the pinned model")
def test_retrieve_returns_k_docs_deterministically() -> None:
    query = "repeated failed SSH login attempts guessing passwords"
    first = retrieve(query)
    assert len(first) == K
    again = retrieve(query)
    assert [d.doc_id for d in first] == [d.doc_id for d in again]
    assert all(isinstance(d.text, str) and d.text for d in first)
