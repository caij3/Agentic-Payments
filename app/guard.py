"""The guard: holds the spending wallet, applies fixed rules, and pays.

The assistant can only *ask* (PaymentRequest). The guard decides:
  approved -> pays through the rail
  held     -> waits for family approval (expires after hold_hours)
  blocked  -> nothing moves, and family cannot release it

Design rules that keep the worst case bounded:
  * The guard never reads `request.claims`. They are recorded and shown as ignored.
  * Rule checks only look at payee, amount, payment type and the guard's own state.
  * Family approval cannot release a blocked type, or more than the wallet holds.
  * Savings are only reachable by a family top-up, never by a payment.
  * If the rail fails, nothing moves.
"""
from __future__ import annotations

import functools
import hmac
import itertools
import math
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .clock import Clock
from .ledger import Ledger
from .rails.base import Rail, Receipt


def _locked(method):
    """One guard action at a time: the API runs requests in parallel threads, and a payment must never
    interleave with another (two approvals of one hold would otherwise both pay, most easily on a
    slow real rail). Reentrant, so actions can call each other."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return wrapper


class GuardError(Exception):
    """A request the guard refuses to carry out (shown to the caller)."""


class NotAuthorized(GuardError):
    """Missing or wrong family key."""


@dataclass
class PaymentRequest:
    payee: str                       # payee id or a free-text name
    amount: float
    type: str = "bill"
    memo: str = ""
    claims: list[str] = field(default_factory=list)   # assistant assertions; never read by rules
    source: str = "assistant"        # who asked: assistant, agent:<name>, scenario
    context: str = ""                # raw text the request came from, for the family to read
    args: dict = field(default_factory=dict)   # passed to the payee (e.g. what to check); never read by rules


@dataclass
class Check:
    rule: str
    label: str
    ok: bool
    detail: str
    on_fail: str                     # "block" or "hold"


@dataclass
class Hold:
    id: str
    created: datetime
    expires: datetime
    payee: dict
    amount: float
    type: str
    memo: str
    source: str
    context: str
    claims: list[str]
    reasons: list[dict]
    status: str = "pending"          # pending, paid, denied, expired, failed
    resolved: datetime | None = None
    receipt: dict | None = None
    report: dict | None = None       # scam-check report; informs family, never changes verdict

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ("created", "expires", "resolved"):
            d[k] = d[k].isoformat(timespec="seconds") if d[k] else None
        return d


@dataclass
class Decision:
    id: str
    verdict: str                     # approved, held, blocked, failed
    payee: dict
    amount: float
    type: str
    checks: list[Check]
    claims_ignored: list[str]
    hold_id: str | None = None
    receipt: dict | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["checks"] = [asdict(c) for c in self.checks]
        return d

    @property
    def failed_checks(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "unknown"


EDITABLE_NUMBERS: dict[str, tuple[float, float, Any]] = {
    "auto_approve_limit": (0, 1000, float),
    "weekly_topup": (0, 2000, float),
    "hold_hours": (1, 168, float),
    "max_payments_per_hour": (1, 20, int),
    "max_per_payee_per_hour": (1, 10, int),
}

TYPE_LABELS = {
    "gift_card": "gift cards",
    "crypto": "cryptocurrency",
    "wire": "wire transfers",
}


class Guard:
    def __init__(self, policy: dict, payees: list[dict], rail: Rail, ledger: Ledger,
                 clock: Clock, family_key: str):
        self.policy = dict(policy)
        self.directory = {p["id"]: dict(p) for p in payees}
        self.rail = rail
        self.ledger = ledger
        self.clock = clock
        self._family_key = family_key
        self._lock = threading.RLock()
        self.known_payees: set[str] = set(self.policy.get("known_payees", []))
        self.wallet = float(self.policy["weekly_topup"])
        self.savings = float(self.policy.get("starting_savings", 0.0))
        self.holds: dict[str, Hold] = {}
        self.payments: list[dict] = []          # completed payments, newest last
        self.decisions: list[Decision] = []
        self._last_weekly_topup = clock.now()
        self._ids = itertools.count(1)
        self.frozen = False
        self.frozen_since: datetime | None = None
        self.ledger.record("opened", wallet=self.wallet, savings=self.savings, rail=rail.name,
                           policy={k: v for k, v in self.policy.items() if k != "starting_savings"})

    # ------------------------------------------------------------------ helpers
    def _next_id(self, prefix: str) -> str:
        return f"{prefix}_{next(self._ids):04d}"

    def _check_key(self, key: str | None) -> None:
        if not key or not hmac.compare_digest(str(key), self._family_key):
            raise NotAuthorized("Family key required")

    def resolve_payee(self, name_or_id: str) -> dict:
        """Find a payee in the directory by id, name or alias. Unknown names become a new payee."""
        q = (name_or_id or "").strip()
        if q in self.directory:
            return dict(self.directory[q])
        ql = q.lower()
        for p in self.directory.values():
            if ql == p["name"].lower() or ql in [a.lower() for a in p.get("aliases", [])]:
                return dict(p)
        pid = _slug(q)
        return {"id": pid, "name": q or "Unknown payee", "aliases": [], "type": "person",
                "qatom_tool": None, "unlisted": True}

    def is_known(self, payee_id: str) -> bool:
        return payee_id in self.known_payees

    def _recent_to_payee(self, payee_id: str) -> int:
        cutoff = self.clock.now() - timedelta(hours=1)
        return sum(1 for p in self.payments if p["at"] >= cutoff and p["payee_id"] == payee_id)

    def _recent_payment_count(self, exempt_only: bool = False) -> int:
        cutoff = self.clock.now() - timedelta(hours=1)
        exempt = set(self.policy.get("rate_limit_exempt_payees", []))
        return sum(1 for p in self.payments
                   if p["at"] >= cutoff and (p["payee_id"] in exempt) == exempt_only)

    # ------------------------------------------------------------------ rules
    def evaluate(self, payee: dict, amount: float, ptype: str) -> list[Check]:
        """The fixed rules. Note what is NOT a parameter: claims, memo, context, report."""
        p = self.policy
        checks: list[Check] = []

        if self.frozen:
            checks.append(Check("not_frozen", "Payments not frozen", False,
                                "Frozen by family: nothing can be paid until they unfreeze", "block"))

        free_item = payee.get("price") is not None and float(payee["price"]) == 0
        valid = isinstance(amount, (int, float)) and math.isfinite(amount) and (amount > 0 or (free_item and amount == 0))
        checks.append(Check("valid_amount", "Valid amount", valid,
                            f"${amount:,.2f}" if valid else f"Invalid amount: {amount!r}", "block"))

        blocked = ptype in p["blocked_types"]
        allowed = ptype in p["allowed_types"]
        if blocked:
            detail = f"{TYPE_LABELS.get(ptype, ptype).capitalize()} are never allowed"
        elif not allowed:
            detail = f"'{ptype}' is not an allowed payment type"
        else:
            detail = f"{ptype.replace('_', ' ').capitalize()} is allowed"
        checks.append(Check("allowed_type", "Allowed payment type", allowed and not blocked, detail, "block"))

        price = payee.get("price")
        if price is not None:
            # A fixed-price payee (the ScamCheck agent) can only ever be paid its price.
            exact = valid and abs(amount - float(price)) < 0.005
            checks.append(Check("fixed_price", "Fixed price", exact,
                                f"{payee['name']} charges ${float(price):,.2f}" if exact
                                else f"{payee['name']} charges ${float(price):,.2f}, not ${amount:,.2f}"
                                if valid else f"{payee['name']} has a fixed price", "block"))

        known = self.is_known(payee["id"])
        checks.append(Check("known_payee", "Known payee", known,
                            f"{payee['name']} is a known payee" if known
                            else f"{payee['name']} has never been paid before", "hold"))

        limit = float(p["auto_approve_limit"])
        under = valid and amount <= limit
        checks.append(Check("under_limit", f"Under the ${limit:,.0f} auto-approve limit", under,
                            f"${amount:,.2f} is within ${limit:,.0f}" if under
                            else f"${amount:,.2f} is over the ${limit:,.0f} limit", "hold"))

        covers = valid and amount <= self.wallet + 1e-9
        checks.append(Check("wallet_covers", "Wallet covers it", covers,
                            f"Wallet has ${self.wallet:,.2f}" if covers
                            else f"Wallet has only ${self.wallet:,.2f}", "hold"))

        cap = int(p["max_payments_per_hour"])
        if payee["id"] in set(p.get("rate_limit_exempt_payees", [])):
            # Exempt from the everyday count (so scam checks don't crowd out bills), but with a cap of its own.
            ecap = int(p.get("max_exempt_per_hour", 10))
            n = self._recent_payment_count(exempt_only=True)
            checks.append(Check("rate_limit", f"At most {ecap} agent purchases an hour", n < ecap,
                                f"{n} of {ecap} agent purchases in the last hour", "hold"))
        else:
            # Repeats to the same payee are the warning sign (a looping agent, a double charge,
            # a scammer milking one account); different payees in an hour are normal life.
            per = int(p.get("max_per_payee_per_hour", 1))
            k = self._recent_to_payee(payee["id"])
            checks.append(Check("repeat_payee", "Not a repeat payment", k < per,
                                f"First payment to {payee['name']} this hour" if k == 0 and k < per
                                else f"{k} of {per} payments to {payee['name']} this hour" if k < per
                                else f"Already paid {payee['name']} {k} time{'s' if k != 1 else ''} this hour",
                                "hold"))
            # Backstop across all payees, so a hijacked assistant can't spread payments around.
            n = self._recent_payment_count()
            checks.append(Check("rate_limit", f"At most {cap} payments an hour", n < cap,
                                f"{n} of {cap} payments in the last hour", "hold"))
        return checks

    # ------------------------------------------------------------------ main entry
    @_locked
    def request(self, req: PaymentRequest) -> Decision:
        self.tick()
        payee = self.resolve_payee(req.payee)
        amount = round(float(req.amount), 2) if isinstance(req.amount, (int, float)) and math.isfinite(req.amount) else req.amount
        checks = self.evaluate(payee, amount, req.type)
        did = self._next_id("req")
        self.ledger.record("request", id=did, source=req.source, payee=payee["id"], payee_name=payee["name"],
                           amount=amount, type=req.type, memo=req.memo,
                           claims_ignored=list(req.claims))

        failed = [c for c in checks if not c.ok]
        decision = Decision(id=did, verdict="approved", payee=payee, amount=amount, type=req.type,
                            checks=checks, claims_ignored=list(req.claims))

        if any(c.on_fail == "block" for c in failed):
            decision.verdict = "blocked"
            self.ledger.record("blocked", id=did, reasons=[c.detail for c in failed if c.on_fail == "block"])
        elif failed:
            now = self.clock.now()
            hold = Hold(id=self._next_id("hold"), created=now,
                        expires=now + timedelta(hours=float(self.policy["hold_hours"])),
                        payee=payee, amount=amount, type=req.type, memo=req.memo, source=req.source,
                        context=req.context, claims=list(req.claims),
                        reasons=[asdict(c) for c in failed])
            self.holds[hold.id] = hold
            decision.verdict = "held"
            decision.hold_id = hold.id
            self.ledger.record("held", id=did, hold=hold.id, reasons=[c.detail for c in failed],
                               expires=hold.expires.isoformat(timespec="seconds"))
        else:
            receipt = self._pay(payee, amount, req.memo, ref=did, args=req.args)
            decision.receipt = receipt.to_dict()
            if not receipt.ok:
                decision.verdict = "failed"
                decision.error = receipt.error

        self.decisions.append(decision)
        return decision

    def _pay(self, payee: dict, amount: float, memo: str, ref: str, args: dict | None = None) -> Receipt:
        if amount > self.wallet + 1e-9:
            # Defence in depth: should be impossible after the checks.
            r = Receipt(ok=False, rail=self.rail.name, amount=amount, error="Wallet does not cover it")
            self.ledger.record("rail_failed", ref=ref, payee=payee["id"], amount=amount, error=r.error)
            return r
        try:
            receipt = self.rail.pay(payee, amount, memo, args)
        except Exception as exc:  # the rail must never take the guard down
            receipt = Receipt(ok=False, rail=self.rail.name, amount=amount, error=f"{type(exc).__name__}: {exc}")
        if receipt.ok:
            self.wallet = round(self.wallet - amount, 2)
            self.payments.append({"at": self.clock.now(), "payee_id": payee["id"], "amount": amount,
                                  "tx_id": receipt.tx_id, "ref": ref})
            self.ledger.record("paid", ref=ref, payee=payee["id"], payee_name=payee["name"], amount=amount,
                               rail=receipt.rail, tx_id=receipt.tx_id, settled=receipt.settled,
                               wallet_after=self.wallet)
        else:
            self.ledger.record("rail_failed", ref=ref, payee=payee["id"], amount=amount,
                               rail=receipt.rail, error=receipt.error)
        return receipt

    # ------------------------------------------------------------------ family actions
    @_locked
    def approve(self, hold_id: str, key: str | None, trust_payee: bool = False) -> Hold:
        self._check_key(key)
        self.tick()
        hold = self._pending(hold_id)
        if self.frozen:
            raise GuardError("Payments are frozen. Unfreeze first.")
        # Family can override "new payee", "over limit" and "rate limit", but never these:
        if hold.type in self.policy["blocked_types"] or hold.type not in self.policy["allowed_types"]:
            raise GuardError("This payment type can never be released")
        if hold.amount > self.wallet + 1e-9:
            raise GuardError(f"The spending wallet has ${self.wallet:,.2f}. Top it up first, "
                             f"or deny this ${hold.amount:,.2f} payment.")
        self.ledger.record("family_approved", hold=hold.id, trust_payee=trust_payee)
        receipt = self._pay(hold.payee, hold.amount, hold.memo, ref=hold.id)
        hold.receipt = receipt.to_dict()
        hold.resolved = self.clock.now()
        if receipt.ok:
            hold.status = "paid"
            if trust_payee and hold.payee["id"] not in self.known_payees:
                self.known_payees.add(hold.payee["id"])
                if hold.payee["id"] not in self.directory:
                    self.directory[hold.payee["id"]] = {k: v for k, v in hold.payee.items() if k != "unlisted"}
                self.ledger.record("payee_trusted", payee=hold.payee["id"], payee_name=hold.payee["name"])
        else:
            hold.status = "failed"
        return hold

    @_locked
    def deny(self, hold_id: str, key: str | None) -> Hold:
        self._check_key(key)
        self.tick()
        hold = self._pending(hold_id)
        hold.status = "denied"
        hold.resolved = self.clock.now()
        self.ledger.record("family_denied", hold=hold.id, payee=hold.payee["id"], amount=hold.amount)
        return hold

    @_locked
    def topup(self, amount: float, key: str | None) -> float:
        self._check_key(key)
        if not (isinstance(amount, (int, float)) and math.isfinite(amount) and amount > 0):
            raise GuardError("Top-up must be a positive amount")
        amount = round(float(amount), 2)
        if amount > self.savings:
            raise GuardError("Not enough in savings")
        self.savings = round(self.savings - amount, 2)
        self.wallet = round(self.wallet + amount, 2)
        self.ledger.record("topup", amount=amount, by="family", wallet_after=self.wallet, savings_after=self.savings)
        return self.wallet

    # ------------------------------------------------------------------ recovery: freeze
    @_locked
    def freeze(self, key: str | None) -> None:
        """Stop every payment, including family approvals, until unfrozen."""
        self._check_key(key)
        if not self.frozen:
            self.frozen = True
            self.frozen_since = self.clock.now()
            self.ledger.record("frozen", by="family")

    @_locked
    def unfreeze(self, key: str | None) -> None:
        self._check_key(key)
        if self.frozen:
            self.frozen = False
            self.frozen_since = None
            self.ledger.record("unfrozen", by="family")

    # ------------------------------------------------------------------ editable rules (family only)
    @_locked
    def update_policy(self, key: str | None, changes: dict) -> dict:
        """Family edits the rules. Every change is validated and written to the ledger.

        The never-allowed list can only grow at runtime: removing gift cards, crypto or wires
        takes a change to policy.json and a restart, not a tap on a phone someone may be coaching.
        """
        self._check_key(key)
        before = {k: self.policy[k] for k in EDITABLE_NUMBERS}
        before["blocked_types"] = list(self.policy["blocked_types"])
        applied: dict[str, Any] = {}
        for name, (lo, hi, cast) in EDITABLE_NUMBERS.items():
            if name in changes and changes[name] is not None:
                v = changes[name]
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
                    raise GuardError(f"{name} must be between {lo} and {hi}")
                applied[name] = cast(v)
        add_blocked = [str(t) for t in changes.get("block_types") or []]
        if any(not t.replace("_", "").isalnum() for t in add_blocked):
            raise GuardError("Bad payment type name")
        if changes.get("unblock_types"):
            raise GuardError("Never-allowed types can't be removed from a phone. Edit policy.json and restart.")
        trust = [str(x) for x in changes.get("trust_payees") or []]
        untrust = [str(x) for x in changes.get("untrust_payees") or []]
        unknown = [x for x in trust if x not in self.directory]
        if unknown:
            raise GuardError(f"Unknown payee: {', '.join(unknown)}")
        if not (applied or add_blocked or trust or untrust):
            raise GuardError("Nothing to change")

        self.policy.update(applied)
        for t in add_blocked:
            if t not in self.policy["blocked_types"]:
                self.policy["blocked_types"] = [*self.policy["blocked_types"], t]
        self.known_payees |= set(trust)
        self.known_payees -= set(untrust)
        after = {k: self.policy[k] for k in EDITABLE_NUMBERS}
        after["blocked_types"] = list(self.policy["blocked_types"])
        self.ledger.record("policy_changed", by="family", before=before, after=after,
                           trusted=trust, untrusted=untrust)
        return after

    @_locked
    def attach_report(self, hold_id: str, report: dict) -> None:
        """Attach a scam-check report to a hold. It is shown to family and changes nothing else."""
        hold = self.holds.get(hold_id)
        if hold is None:
            return
        hold.report = dict(report)
        self.ledger.record("report_attached", hold=hold_id, risk=report.get("risk"),
                           source=report.get("source"), cost=report.get("cost"))

    def _pending(self, hold_id: str) -> Hold:
        hold = self.holds.get(hold_id)
        if hold is None:
            raise GuardError("No such hold")
        if hold.status != "pending":
            raise GuardError(f"This hold is already {hold.status}")
        return hold

    # ------------------------------------------------------------------ time
    @_locked
    def tick(self) -> None:
        """Expire old holds and run the weekly top-up. Called before every action."""
        now = self.clock.now()
        for hold in self.holds.values():
            if hold.status == "pending" and now >= hold.expires:
                hold.status = "expired"
                hold.resolved = now
                self.ledger.record("expired", hold=hold.id, payee=hold.payee["id"], amount=hold.amount,
                                   note="No family answer in time. Cancelled, nothing moved.")
        while now - self._last_weekly_topup >= timedelta(days=7):
            self._last_weekly_topup += timedelta(days=7)
            target = float(self.policy["weekly_topup"])
            move = round(min(max(target - self.wallet, 0.0), self.savings), 2)
            if move > 0:
                self.savings = round(self.savings - move, 2)
                self.wallet = round(self.wallet + move, 2)
            self.ledger.record("weekly_topup", amount=move, wallet_after=self.wallet, savings_after=self.savings)

    # ------------------------------------------------------------------ views
    @_locked
    def snapshot(self) -> dict[str, Any]:
        ok, bad = self.ledger.verify()
        return {
            "wallet": self.wallet,
            "savings": self.savings,
            "frozen": self.frozen,
            "frozen_since": self.frozen_since.isoformat(timespec="seconds") if self.frozen_since else None,
            "weekly_topup": self.policy["weekly_topup"],
            "known_payees": sorted(self.known_payees),
            "holds": [h.to_dict() for h in sorted(self.holds.values(), key=lambda h: h.created, reverse=True)],
            "payments": [{**p, "at": p["at"].isoformat(timespec="seconds")} for p in self.payments],
            "decisions": [d.to_dict() for d in self.decisions[-30:]],
            "ledger": {"ok": ok, "first_bad": bad, "head": self.ledger.head(), "entries": self.ledger.entries},
        }
