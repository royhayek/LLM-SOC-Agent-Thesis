"""Tests for the curated knowledge base (E5-02, SCRUM-34)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

DOCS = Path(__file__).resolve().parent.parent / "knowledge" / "docs"
FAMILIES = (
    "ssh_brute_force",
    "port_scan",
    "mqtt_publish_flood",
    "mqtt_brute_force",
    "syn_flood",
    "botnet",
)


def _doc_files() -> list[Path]:
    return sorted(p for p in DOCS.glob("*.md") if p.name != "INDEX.md")


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name} has no frontmatter"
    _, block, _ = text.split("---\n", 2)
    data = yaml.safe_load(block)
    assert isinstance(data, dict), f"{path.name} frontmatter is not a mapping"
    return data


def test_doc_count_is_between_50_and_200() -> None:
    assert 50 <= len(_doc_files()) <= 200


@pytest.mark.parametrize("path", _doc_files(), ids=lambda p: p.name)
def test_every_doc_has_source(path: Path) -> None:
    source = _frontmatter(path).get("source")
    assert isinstance(source, str) and source.strip(), f"{path.name} lacks a non-empty source"


def test_index_maps_each_family_to_at_least_three_docs() -> None:
    index = (DOCS / "INDEX.md").read_text(encoding="utf-8")
    for family in FAMILIES:
        line = next((ln for ln in index.splitlines() if f"**{family}**" in ln), None)
        assert line is not None, f"{family} missing from INDEX.md"
        docs = [tok.strip(" ,`") for tok in line.split() if tok.strip(" ,`").endswith(".md")]
        assert len(docs) >= 3, f"{family} maps to fewer than 3 docs"
        for doc in docs:
            assert (DOCS / doc).exists(), f"{family} references missing doc {doc}"


def test_index_states_vulnerability_databases_out_of_scope() -> None:
    index = (DOCS / "INDEX.md").read_text(encoding="utf-8").lower()
    assert "out of scope" in index and "vulnerability database" in index
