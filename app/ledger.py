"""Hash-chained record of every decision.

Each entry stores the hash of the entry before it, so changing or deleting a
past entry breaks every hash after it. `verify()` finds the first broken link.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .clock import Clock

GENESIS = "0" * 64
_HASHED_FIELDS = ("seq", "ts", "kind", "data", "prev")


def _digest(entry: dict) -> str:
    body = {k: entry[k] for k in _HASHED_FIELDS}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


class Ledger:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.entries: list[dict] = []

    def record(self, kind: str, **data: Any) -> dict:
        entry = {
            "seq": len(self.entries),
            "ts": self.clock.now().isoformat(timespec="seconds"),
            "kind": kind,
            "data": json.loads(json.dumps(data, default=str)),
            "prev": self.entries[-1]["hash"] if self.entries else GENESIS,
        }
        entry["hash"] = _digest(entry)
        self.entries.append(entry)
        return entry

    def verify(self) -> tuple[bool, int | None]:
        """Return (ok, seq of the first bad entry or None)."""
        prev = GENESIS
        for i, entry in enumerate(self.entries):
            if entry.get("seq") != i or entry.get("prev") != prev or entry.get("hash") != _digest(entry):
                return False, i
            prev = entry["hash"]
        return True, None

    def head(self) -> str:
        return self.entries[-1]["hash"] if self.entries else GENESIS
