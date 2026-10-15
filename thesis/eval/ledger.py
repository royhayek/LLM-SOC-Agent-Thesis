"""The completion ledger for the condition-matrix runner (E9-01, SCRUM-41).

A full run is ~12,000+ calls, so it must survive interruption without duplicating or losing work.
Each finished (bundle, condition, repetition) is recorded as one append-only JSONL line, keyed by
`(bundle_id, config_hash, repetition)` — never by bundle id alone, which would repeat or skip whole
conditions (the gotcha). On restart, the ledger is loaded and finished items are skipped.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LedgerKey:
    bundle_id: str
    config_hash: str
    repetition: int

    def as_row(self) -> dict[str, object]:
        return {
            "bundle_id": self.bundle_id,
            "config_hash": self.config_hash,
            "repetition": self.repetition,
        }


class Ledger:
    """Append-only record of finished (bundle, condition, repetition) items; concurrency-safe."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._done: set[tuple[str, str, int]] = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._done.add((row["bundle_id"], row["config_hash"], int(row["repetition"])))

    def is_done(self, key: LedgerKey) -> bool:
        return (key.bundle_id, key.config_hash, key.repetition) in self._done

    def mark(self, key: LedgerKey) -> None:
        """Record one finished item. Idempotent: marking a done item writes nothing new."""
        tup = (key.bundle_id, key.config_hash, key.repetition)
        with self._lock:
            if tup in self._done:
                return
            self._done.add(tup)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as sink:
                sink.write(json.dumps(key.as_row(), sort_keys=True) + "\n")

    def __len__(self) -> int:
        return len(self._done)


__all__ = ["Ledger", "LedgerKey"]
