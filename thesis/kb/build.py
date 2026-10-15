"""Embed the curated knowledge base into a numpy index (E5-03, SCRUM-42).

For 50–200 documents, a numpy array with cosine similarity is faster, simpler and fully
deterministic — no vector database, which would be a component needing its own characterisation
(record §6.2, ADR-0000). The embedding model is pinned by revision, like the LLM (§4.2), and the
build runs on CPU so the saved floats, and therefore the file hash, are stable (GPU/Metal backends
would differ).

    python -m thesis.kb.build      # writes knowledge/index/{embeddings.npy,doc_ids.json,meta.json}

Running it twice produces byte-identical `.npy` files (AC1): the document order is sorted, encoding
is on CPU in float32, and inference has no randomness.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "knowledge" / "docs"
INDEX_DIR = REPO_ROOT / "knowledge" / "index"

EMBEDDINGS_PATH = INDEX_DIR / "embeddings.npy"
DOC_IDS_PATH = INDEX_DIR / "doc_ids.json"
META_PATH = INDEX_DIR / "meta.json"

# Pinned embedding model (sentence-transformers, record §6.2). Revision read from the Hugging Face
# Hub API on 2026-10-15, recorded here and in meta.json so the index is reproducible (§4.2).
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


def _doc_text(path: Path) -> str:
    """The document's embeddable text: title and body, without the YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        _, _, text = text.split("---\n", 2)
    return text.strip()


def _doc_paths() -> list[Path]:
    # Sort by stem (the doc id), so the row order matches doc_ids and is stable regardless of the
    # ".md" suffix affecting prefix names (e.g. technique-t1110 vs technique-t1110-001).
    return sorted((p for p in DOCS_DIR.glob("*.md") if p.name != "INDEX.md"), key=lambda p: p.stem)


def build(out_dir: Path = INDEX_DIR) -> dict[str, object]:
    from sentence_transformers import SentenceTransformer

    paths = _doc_paths()
    doc_ids = [p.stem for p in paths]
    texts = [_doc_text(p) for p in paths]

    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu")
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,  # unit vectors, so cosine similarity is a dot product
        show_progress_bar=False,
        batch_size=32,
    ).astype(np.float32)

    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "embeddings.npy", embeddings, allow_pickle=False)
    (out_dir / "doc_ids.json").write_text(json.dumps(doc_ids, indent=2) + "\n", encoding="utf-8")
    meta = {
        "model": MODEL_NAME,
        "revision": MODEL_REVISION,
        "dim": int(embeddings.shape[1]),
        "n_docs": len(doc_ids),
        "normalized": True,
        "device": "cpu",
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return meta


def main() -> int:
    meta = build()
    print(f"embedded {meta['n_docs']} docs, dim {meta['dim']}, model {MODEL_REVISION[:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
