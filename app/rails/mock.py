"""Practice rail: in-memory balances, no real money."""
from __future__ import annotations

import itertools

from .base import Receipt


class MockRail:
    name = "practice"

    def __init__(self) -> None:
        self.received: dict[str, float] = {}
        self.down = False          # set True to simulate an outage
        self._ids = itertools.count(1)

    def pay(self, payee: dict, amount: float, memo: str, args: dict | None = None) -> Receipt:
        if self.down:
            return Receipt(ok=False, rail=self.name, amount=amount, error="Practice rail is down")
        pid = payee["id"]
        self.received[pid] = round(self.received.get(pid, 0.0) + amount, 2)
        tx = f"prac_{next(self._ids):05d}"
        return Receipt(ok=True, rail=self.name, amount=amount, settled=f"${amount:,.2f}", tx_id=tx,
                       raw={"payee": pid, "memo": memo})

    def status(self) -> str:
        return "Practice rail: offline" if self.down else "Practice rail: ready (no real money)"
