"""Qatom rail. Each payee is a catalog item on Qatom; paying means buying it.

* The guard tracks the spending wallet in demo dollars. Qatom settles the item's
  own fixed price (catalog prices are fixed per item) and is the proof money moved.
* Payees with no `qatom_item` in payees.json settle on the practice rail when
  QATOM_UNMAPPED=practice (the default), and the receipt says so. Set it to
  `fail` to refuse them instead.
"""
from __future__ import annotations

import os

from .base import Receipt
from .mock import MockRail
from .qatom_client import QatomClient, QatomError


class QatomRail:
    name = "qatom"

    def __init__(self, client: QatomClient | None = None, unmapped: str | None = None):
        self.client = client or QatomClient()
        self.unmapped = (unmapped or os.getenv("QATOM_UNMAPPED") or "practice").strip().lower()
        self.practice = MockRail()
        self.last_error: str | None = None

    def pay(self, payee: dict, amount: float, memo: str, args: dict | None = None) -> Receipt:
        item = payee.get("qatom_item")
        if not item:
            if self.unmapped == "practice":
                r = self.practice.pay(payee, amount, memo, args)
                r.rail = "practice (no Qatom item for this payee)"
                return r
            return Receipt(ok=False, rail=self.name, amount=amount, error=f"{payee['name']} has no Qatom item")
        args = {**(payee.get("qatom_args") or {}), **(args or {})}
        try:
            res = self.client.pay_item(int(item), args)
        except QatomError as exc:
            self.last_error = str(exc)
            return Receipt(ok=False, rail=self.name, amount=amount, error=str(exc)[:300])
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return Receipt(ok=False, rail=self.name, amount=amount, error=self.last_error[:300])
        settled = f"{res.get('charged') or '?'} {res.get('currency') or 'USD-TDN'}"
        if res.get("delivery_failed"):
            settled += " (paid; delivery failed, not retried)"
        return Receipt(ok=True, rail=self.name, amount=amount, settled=settled, tx_id=res.get("tx_id"),
                       raw={"body": res.get("body"), "catalog_item_id": item})

    def status(self) -> str:
        if self.client.mode == "none":
            return "Qatom: not signed in"
        try:
            return f"Qatom ({self.client.mode} token): agent wallet {self.client.agent_balance()}"
        except Exception as exc:
            return f"Qatom: {str(exc)[:160]}"
