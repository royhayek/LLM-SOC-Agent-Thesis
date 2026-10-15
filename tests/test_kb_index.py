"""Tests for the knowledge-base embedding index (E5-03, SCRUM-42)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from thesis.kb.build import (
    DOC_IDS_PATH,
    EMBEDDINGS_PATH,
    META_PATH,
    MODEL_NAME,
    MODEL_REVISION,
)

_HAS_ST = importlib.util.find_spec("sentence_transformers") is not None


def test_committed_index_is_consistent() -> None:
    embeddings = np.load(EMBEDDINGS_PATH)
    doc_ids = json.loads(DOC_IDS_PATH.read_text(encoding="utf-8"))
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    assert embeddings.shape[0] == len(doc_ids) == meta["n_docs"]
    assert embeddings.shape[1] == meta["dim"]
    assert embeddings.dtype == np.float32
    assert meta["model"] == MODEL_NAME and meta["revision"] == MODEL_REVISION


def test_doc_ids_match_the_committed_documents() -> None:
    docs_dir = Path(__file__).resolve().parent.parent / "knowledge" / "docs"
    on_disk = sorted(p.stem for p in docs_dir.glob("*.md") if p.name != "INDEX.md")
    assert json.loads(DOC_IDS_PATH.read_text(encoding="utf-8")) == on_disk


def test_embeddings_are_unit_normalized() -> None:
    norms = np.linalg.norm(np.load(EMBEDDINGS_PATH), axis=1)
    assert np.allclose(norms, 1.0, atol=1e-3)  # normalized, so cosine == dot product


@pytest.mark.slow
@pytest.mark.skipif(not _HAS_ST, reason="needs sentence-transformers + the pinned model")
def test_rebuild_is_byte_identical(tmp_path: Path) -> None:
    from thesis.kb.build import build

    build(tmp_path / "a")
    build(tmp_path / "b")
    h_a = hashlib.sha256((tmp_path / "a" / "embeddings.npy").read_bytes()).hexdigest()
    h_b = hashlib.sha256((tmp_path / "b" / "embeddings.npy").read_bytes()).hexdigest()
    assert h_a == h_b
