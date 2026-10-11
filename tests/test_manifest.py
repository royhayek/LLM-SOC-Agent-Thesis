"""Tests for the corpus manifest (E2-06, SCRUM-62).

Exercised on a tiny temporary corpus so the test is fast and self-contained: build, verify an
unchanged copy (clean), then flip one byte and confirm verify names that file.
"""

from __future__ import annotations

import json
from pathlib import Path

from thesis.corpus import manifest

DIRS = (Path("data/raw/corpus-v1.0.0"), Path("data/labels"))
MAN = Path("data/corpus-manifest.json")
SHA = Path("data/corpus-manifest.sha256")


def _make_corpus(root: Path) -> None:
    (root / "data/raw/corpus-v1.0.0/run1").mkdir(parents=True)
    (root / "data/labels").mkdir(parents=True)
    (root / "data/raw/corpus-v1.0.0/run1/flows.jsonl").write_text("a\nb\n", encoding="utf-8")
    (root / "data/raw/corpus-v1.0.0/run1/execution_log.jsonl").write_text("{}\n", encoding="utf-8")
    (root / "data/labels/run1.parquet").write_bytes(b"\x00\x01\x02\x03")


def test_build_lists_path_size_and_sha_for_every_file(tmp_path: Path) -> None:
    _make_corpus(tmp_path)
    m = manifest.build(DIRS, MAN, SHA, root=tmp_path)
    assert m["file_count"] == 3
    for entry in m["files"]:  # type: ignore[attr-defined]
        assert set(entry) == {"path", "size", "sha256"}
        assert len(entry["sha256"]) == 64
    paths = {e["path"] for e in m["files"]}  # type: ignore[attr-defined]
    assert "data/labels/run1.parquet" in paths


def test_verify_clean_corpus_has_no_problems(tmp_path: Path) -> None:
    _make_corpus(tmp_path)
    manifest.build(DIRS, MAN, SHA, root=tmp_path)
    assert manifest.verify(DIRS, MAN, root=tmp_path) == []


def test_verify_flags_a_changed_byte_and_names_the_file(tmp_path: Path) -> None:
    _make_corpus(tmp_path)
    manifest.build(DIRS, MAN, SHA, root=tmp_path)
    target = tmp_path / "data/raw/corpus-v1.0.0/run1/flows.jsonl"
    target.write_text("a\nX\n", encoding="utf-8")  # same length, one byte changed
    problems = manifest.verify(DIRS, MAN, root=tmp_path)
    assert any("content changed" in p and "flows.jsonl" in p for p in problems)


def test_verify_flags_a_missing_and_an_extra_file(tmp_path: Path) -> None:
    _make_corpus(tmp_path)
    manifest.build(DIRS, MAN, SHA, root=tmp_path)
    (tmp_path / "data/labels/run1.parquet").unlink()
    (tmp_path / "data/raw/corpus-v1.0.0/run1/new.txt").write_text("x", encoding="utf-8")
    problems = manifest.verify(DIRS, MAN, root=tmp_path)
    assert any("missing" in p and "run1.parquet" in p for p in problems)
    assert any("unexpected" in p and "new.txt" in p for p in problems)


def test_manifest_own_sha256_is_written_and_matches(tmp_path: Path) -> None:
    _make_corpus(tmp_path)
    manifest.build(DIRS, MAN, SHA, root=tmp_path)
    import hashlib

    text = (tmp_path / MAN).read_text(encoding="utf-8")
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert (tmp_path / SHA).read_text(encoding="utf-8").split()[0] == expected


def test_hidden_files_are_excluded(tmp_path: Path) -> None:
    _make_corpus(tmp_path)
    (tmp_path / "data/raw/corpus-v1.0.0/run1/.DS_Store").write_bytes(b"junk")
    m = manifest.build(DIRS, MAN, SHA, root=tmp_path)
    assert all(".DS_Store" not in e["path"] for e in m["files"])  # type: ignore[attr-defined]
    assert manifest.verify(DIRS, MAN, root=tmp_path) == []  # hidden file does not break verify


def test_build_is_deterministic(tmp_path: Path) -> None:
    _make_corpus(tmp_path)
    manifest.build(DIRS, MAN, SHA, root=tmp_path)
    first = (tmp_path / MAN).read_text(encoding="utf-8")
    manifest.build(DIRS, MAN, SHA, root=tmp_path)
    assert (tmp_path / MAN).read_text(encoding="utf-8") == first
    assert json.loads(first)["file_count"] == 3
