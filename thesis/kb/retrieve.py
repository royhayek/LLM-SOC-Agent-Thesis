"""The deterministic knowledge-base retrieval tool (E5-04, SCRUM-51).

Retrieval is node 1's only tool, but it is plain deterministic code, not an LLM call (record §6.3):
the same query returns the same documents in the same order every time, so runs reproduce. It
embeds the query with the pinned model (E5-03), scores the committed index by cosine similarity
(the vectors are unit-normalised, so cosine is a dot product), and returns the top k = 3 documents,
breaking ties by ascending document id (METHODS.md changelog 17).

`device_context()` returns a device's inventory entry (E5-01) — its role and criticality are the
context node 1 needs, and criticality is what can make an action contextually unsafe (§3.1).

The query is built from bundle content, which includes attacker-controlled text. Retrieval itself
is safe (no code from the query runs), but every query and its result ids are logged so a strange
retrieval can be traced (ticket gotcha).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import structlog
import yaml  # type: ignore[import-untyped]

from thesis.kb.build import (
    DOC_IDS_PATH,
    DOCS_DIR,
    EMBEDDINGS_PATH,
    MODEL_NAME,
    MODEL_REVISION,
    _doc_text,
)

K = 3  # locked in METHODS.md changelog 17; a change re-runs the affected conditions.

_INVENTORY = Path(__file__).resolve().parents[2] / "knowledge" / "devices.yaml"

_log = structlog.get_logger("thesis.kb.retrieve")


@dataclass(frozen=True)
class RetrievedDoc:
    doc_id: str
    score: float
    text: str


_index: tuple[np.ndarray, list[str]] | None = None
_model: object = None


def _load_index() -> tuple[np.ndarray, list[str]]:
    global _index
    if _index is None:
        embeddings = np.load(EMBEDDINGS_PATH).astype(np.float32)
        doc_ids = json.loads(DOC_IDS_PATH.read_text(encoding="utf-8"))
        _index = (embeddings, doc_ids)
    return _index


def rank(
    query_vec: np.ndarray, embeddings: np.ndarray, doc_ids: list[str], k: int
) -> list[tuple[str, float]]:
    """Top-k (doc_id, score) by cosine similarity; ties broken by ascending doc_id. Pure."""
    sims = embeddings @ query_vec
    order = sorted(range(len(doc_ids)), key=lambda i: (-float(sims[i]), doc_ids[i]))
    return [(doc_ids[i], round(float(sims[i]), 6)) for i in order[:k]]


def _embed_query(query: str) -> np.ndarray:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu")
    vec = _model.encode(  # type: ignore[attr-defined]
        [query], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
    )
    return cast("np.ndarray", np.asarray(vec[0], dtype=np.float32))


def retrieve(query: str, k: int = K) -> list[RetrievedDoc]:
    """Return the top-k knowledge-base documents for `query`, deterministically."""
    embeddings, doc_ids = _load_index()
    ranked = rank(_embed_query(query), embeddings, doc_ids, k)
    _log.info("kb_retrieve", query=query, doc_ids=[d for d, _ in ranked])
    return [
        RetrievedDoc(doc_id=d, score=s, text=_doc_text(DOCS_DIR / f"{d}.md")) for d, s in ranked
    ]


def device_context(device_id: str) -> dict[str, str]:
    """Return the inventory entry (id, role, criticality, ip, position) for `device_id` (E5-01)."""
    data = yaml.safe_load(_INVENTORY.read_text(encoding="utf-8"))
    for entry in data["devices"] + data.get("infrastructure", []):
        if entry["id"] == device_id:
            return {str(key): str(value) for key, value in entry.items()}
    raise KeyError(f"unknown device {device_id!r}")


__all__ = ["K", "RetrievedDoc", "device_context", "rank", "retrieve"]
