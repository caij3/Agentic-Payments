"""What every payment rail must provide. The guard only talks to this."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass
class Receipt:
    ok: bool
    rail: str
    amount: float                 # demo dollars the guard asked to move
    settled: str = ""             # what actually settled on the rail, human readable
    tx_id: str | None = None
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class Rail(Protocol):
    name: str

    def pay(self, payee: dict, amount: float, memo: str) -> Receipt: ...

    def status(self) -> str: ...
