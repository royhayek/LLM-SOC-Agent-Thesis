"""Corpus manifest: a SHA-256 per file, so the frozen corpus is immutable and verifiable (E2-06).

    python -m thesis.corpus.manifest build    # write data/corpus-manifest.json (+ .sha256)
    python -m thesis.corpus.manifest verify    # exit 0 iff every file matches the manifest

The manifest lets anyone prove the data under a result is the data that was frozen (record §6.7).
`build` is deterministic (files sorted by path, canonical JSON), so re-running it on an unchanged
corpus rewrites the identical bytes. `verify` reports every changed, missing or unexpected file
and exits non-zero if there is one. Hidden files (`.DS_Store` and the like) are excluded, so a
macOS folder-walk artifact never breaks verification.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIRS = (Path("data/raw/corpus-v1.0.0-rc"), Path("data/labels"))
MANIFEST_PATH = Path("data/corpus-manifest.json")
SHA_PATH = Path("data/corpus-manifest.sha256")
_CHUNK = 1 << 20  # 1 MiB streaming read


def _is_hidden(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def iter_corpus_files(dirs: tuple[Path, ...], root: Path) -> list[Path]:
    """Every non-hidden file under each dir, as paths relative to `root`, sorted for determinism."""
    found: list[Path] = []
    for d in dirs:
        base = root / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and not _is_hidden(p.relative_to(root)):
                found.append(p.relative_to(root))
    return sorted(found, key=lambda p: p.as_posix())


def build_manifest(dirs: tuple[Path, ...], root: Path) -> dict[str, object]:
    files = [
        {
            "path": rel.as_posix(),
            "size": (root / rel).stat().st_size,
            "sha256": sha256_file(root / rel),
        }
        for rel in iter_corpus_files(dirs, root)
    ]
    return {"corpus": "corpus-v1.0.0-rc", "file_count": len(files), "files": files}


def _dump(manifest: dict[str, object]) -> str:
    # Canonical: sorted keys, trailing newline, so the bytes are stable across runs and machines.
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def build(
    dirs: tuple[Path, ...] = CORPUS_DIRS,
    manifest_path: Path = MANIFEST_PATH,
    sha_path: Path = SHA_PATH,
    root: Path = REPO_ROOT,
) -> dict[str, object]:
    manifest = build_manifest(dirs, root)
    text = _dump(manifest)
    (root / manifest_path).write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    (root / sha_path).write_text(f"{digest}  {manifest_path.as_posix()}\n", encoding="utf-8")
    return manifest


def verify(
    dirs: tuple[Path, ...] = CORPUS_DIRS,
    manifest_path: Path = MANIFEST_PATH,
    root: Path = REPO_ROOT,
) -> list[str]:
    """Return a list of problems (empty means the corpus matches the manifest)."""
    manifest = json.loads((root / manifest_path).read_text(encoding="utf-8"))
    recorded = {f["path"]: f for f in manifest["files"]}
    on_disk = {p.as_posix() for p in iter_corpus_files(dirs, root)}

    problems: list[str] = []
    for path in sorted(set(recorded) - on_disk):
        problems.append(f"missing: {path}")
    for path in sorted(on_disk - set(recorded)):
        problems.append(f"unexpected (not in manifest): {path}")
    for path in sorted(set(recorded) & on_disk):
        rec = recorded[path]
        actual_size = (root / path).stat().st_size
        if actual_size != rec["size"]:
            problems.append(f"size changed: {path} ({rec['size']} -> {actual_size})")
        elif sha256_file(root / path) != rec["sha256"]:
            problems.append(f"content changed: {path}")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in ("build", "verify"):
        print("usage: python -m thesis.corpus.manifest {build|verify}", file=sys.stderr)
        return 2
    if args[0] == "build":
        manifest = build()
        print(f"wrote {MANIFEST_PATH} ({manifest['file_count']} files) and {SHA_PATH}")
        return 0
    problems = verify()
    if problems:
        print(f"corpus does NOT match the manifest ({len(problems)} problem(s)):", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print("corpus matches the manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
