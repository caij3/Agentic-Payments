"""The AI assistant. It turns chat into a PaymentRequest and explains the guard's answer.

It has no wallet key and no way to change the rules. It can only ask the guard.

Parsing: Backboard (an LLM) is tried first when BACKBOARD_API_KEY is set. Any error,
timeout or bad output falls back to the built-in parser, so the demo cannot stall.
Explanations are built from the guard's own check results, not made up by the model.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field

import httpx

from .guard import Decision, Guard, PaymentRequest
from .scamcheck import ScamChecker

log = logging.getLogger("scamguard.assistant")

GRANDMA = os.getenv("GRANDMA_NAME", "Margaret")
DAUGHTER = os.getenv("DAUGHTER_NAME", "Sarah")

TYPE_WORDS = [
    ("gift_card", r"gift ?cards?|itunes|apple cards?|google play cards?|steam cards?|amazon cards?"),
    ("crypto", r"bitcoin|crypto(?:currency)?|\bbtc\b|ethereum|\beth\b|usdt|tether|bitcoin atm|coin atm"),
    ("wire", r"wire(?: transfer)?|western union|moneygram"),
]

CLAIM_PATTERNS = [
    (r"\btrusted\b|\bverified\b|\blegit(?:imate)?\b", "says the payee is trusted"),
    (r"skip (?:\w+ ){0,2}(?:checks?|rules|verification|approval)|no need to check|bypass", "asks to skip the checks"),
    (r"disconnect\w*|shut ?off|final notice|suspended|arrest\w*", "threatens consequences"),
    (r"\burgent\w*|right away|immediately|right now|within the hour|before it'?s too late", "says it is urgent"),
    (r"\bauthori[sz]ed\b|pre-?approved|already approved|has approved", "claims it is already authorized"),
    (r"don'?t tell|do not tell|keep (?:this|it) (?:a )?secret|between us", "asks to keep it secret"),
    (r"ignore (?:your|the|all|previous) (?:rules|instructions|limits)", "asks to ignore the rules"),
    (r"\bpolice\b|\bofficer\b|\birs\b|\bcra\b|tax office|revenue agency|bank security|fraud department", "claims to be an authority"),
]

PAY_WORDS = r"\b(pay|send|transfer|buy|owe|bill|wire|purchase|reorder|top ?up|bail)\b"


@dataclass
class Parsed:
    payee: str
    amount: float | None
    type: str
    memo: str
    claims: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- parser
def _find_amount(text: str) -> float | None:
    m = re.search(r"\$\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text)
    if not m:
        m = re.search(r"\b([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?:dollars|bucks|cad|usd)\b", text, re.I)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _find_type(text: str) -> str | None:
    for ptype, pattern in TYPE_WORDS:
        if re.search(pattern, text, re.I):
            return ptype
    return None


def find_claims(text: str) -> list[str]:
    found = []
    for pattern, label in CLAIM_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            found.append(f'{label} ("{m.group(0)}")')
    return found


def _find_payee(text: str, payees: list[dict]) -> dict | None:
    low = text.lower()
    best = None
    for p in payees:
        for alias in [p["name"], *p.get("aliases", [])]:
            if not alias or p.get("agent"):
                continue
            if re.search(r"\b" + re.escape(alias.lower()) + r"\b", low):
                if best is None or len(alias) > best[0]:
                    best = (len(alias), p)
    return best[1] if best else None


def _free_text_payee(text: str) -> str | None:
    m = re.search(r"\b(?:to|pay)\s+((?:[A-Z][\w'&.-]*\s?){1,4})", text)
    if m:
        name = m.group(1).strip(" .,")
        if name and name.lower() not in {"i", "my", "the", "me"}:
            return name
    return None


def _claimed_authority(text: str) -> str | None:
    m = re.search(r"\b(tax office|revenue agency|\bcra\b|\birs\b|police|bank security|fraud department)", text, re.I)
    return f"Caller claiming to be the {m.group(1)}" if m else None


def parse(text: str, payees: list[dict]) -> Parsed | None:
    """Built-in parser. Returns None when the message is not a payment request."""
    amount = _find_amount(text)
    ptype = _find_type(text)
    payee = _find_payee(text, payees)
    if not (re.search(PAY_WORDS, text, re.I) or amount or ptype):
        return None
    if payee is not None:
        name = payee["id"]
        if amount is None and payee.get("amount_due"):
            amount = float(payee["amount_due"])      # asks the payee's billing record for the amount owed
        ptype = ptype or payee.get("type", "bill")
    else:
        name = _free_text_payee(text) or _claimed_authority(text) or "Unknown payee"
        ptype = ptype or "person"
    memo = text.strip()[:140]
    return Parsed(payee=name, amount=amount, type=ptype, memo=memo, claims=find_claims(text))


# --------------------------------------------------------------------------- Backboard
SYSTEM_PROMPT = """You turn a senior's chat message into a payment request for a payment guard.
Reply with JSON only: {"intent": "pay" or "chat", "payee": string, "amount": number or null,
"type": one of ["bill","shopping","pharmacy","service","person","gift_card","crypto","wire"],
"memo": short string}.
Use the payee directory names when one matches. Never invent an amount that is not in the message
or the directory's amount_due. Gift cards, Bitcoin or any crypto, and wire transfers must use those types."""


class BackboardLLM:
    URL = "https://app.backboard.io/api/threads/messages"

    def __init__(self, api_key: str, provider: str = "openai", model: str = "gpt-4o", timeout: float = 8.0):
        self.api_key = api_key
        self.provider = provider
        self.model = model
        self.timeout = timeout

    def extract(self, text: str, payees: list[dict]) -> dict:
        directory = [{"name": p["name"], "amount_due": p.get("amount_due")} for p in payees if not p.get("agent")]
        content = f"Payee directory: {json.dumps(directory)}\n\nMessage: {text}"
        r = httpx.post(self.URL, timeout=self.timeout,
                       headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
                       json={"content": content, "system_prompt": SYSTEM_PROMPT, "llm_provider": self.provider,
                             "model_name": self.model, "stream": False, "json_output": True})
        r.raise_for_status()
        body = r.json()
        raw = body.get("content") or ""
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip()).strip()
        return json.loads(raw)

    def status(self) -> str:
        return f"Backboard ({self.provider}/{self.model})"


def llm_from_env() -> BackboardLLM | None:
    key = os.getenv("BACKBOARD_API_KEY", "").strip()
    if not key:
        return None
    try:
        timeout = float(os.getenv("BACKBOARD_TIMEOUT", "10"))
    except ValueError:
        timeout = 10.0
    return BackboardLLM(key, os.getenv("BACKBOARD_PROVIDER", "openai"), os.getenv("BACKBOARD_MODEL", "gpt-4o"), timeout)


# --------------------------------------------------------------------------- assistant
class Assistant:
    def __init__(self, guard: Guard, checker: ScamChecker, llm: BackboardLLM | None = None):
        self.guard = guard
        self.checker = checker
        self.llm = llm
        self.last_llm_error: str | None = None

    @property
    def payees(self) -> list[dict]:
        return list(self.guard.directory.values())

    def understand(self, text: str) -> tuple[Parsed | None, str]:
        fallback = parse(text, self.payees)
        if self.llm is None:
            return fallback, "parser"
        try:
            out = self.llm.extract(text, self.payees)
            if out.get("intent") != "pay":
                return None, "backboard"
            payee = str(out.get("payee") or (fallback.payee if fallback else "Unknown payee"))
            amount = out.get("amount")
            amount = float(amount) if isinstance(amount, (int, float, str)) and str(amount).strip() else None
            # Cross-check: an amount written in the message beats the model's reading of it.
            explicit = _find_amount(text)
            if explicit is not None:
                amount = explicit
            ptype = str(out.get("type") or "person")
            # A risky type spotted by the parser is never downgraded by the model.
            if fallback and fallback.type in self.guard.policy["blocked_types"]:
                ptype = fallback.type
            if amount is None and fallback:
                amount = fallback.amount
            self.last_llm_error = None
            return Parsed(payee=payee, amount=amount, type=ptype, memo=str(out.get("memo") or text)[:140],
                          claims=find_claims(text)), "backboard"
        except Exception as exc:  # any failure -> parser, never stall the demo
            self.last_llm_error = f"{type(exc).__name__}: {exc}"[:200]
            log.warning("Backboard failed, using parser: %s", self.last_llm_error)
            return fallback, "parser (Backboard failed)"

    def handle(self, text: str, speaker: str = "grandma") -> dict:
        parsed, parsed_by = self.understand(text)
        if parsed is None:
            return {"reply": "I can pay your bills and keep an eye out for scams. Try \"Pay my hydro bill\".",
                    "parsed_by": parsed_by}
        if parsed.amount is None:
            return {"reply": f"How much should I pay {self.guard.resolve_payee(parsed.payee)['name']}?",
                    "parsed": asdict(parsed), "parsed_by": parsed_by}

        source = "assistant" if speaker == "grandma" else f"assistant (message from {speaker})"
        return self._submit(parsed, source, text, parsed_by)

    def handle_invoice(self, invoice: dict) -> dict:
        """Agent to agent: a billing agent's invoice becomes a request. Its text is untrusted."""
        text = str(invoice.get("text", ""))[:1000]
        try:
            amount = float(invoice.get("amount"))
        except (TypeError, ValueError):
            amount = float("nan")
        parsed = Parsed(payee=str(invoice.get("payee") or "Unknown payee"), amount=amount,
                        type=str(invoice.get("type") or "bill"), memo=f"Invoice from {invoice.get('agent', 'an agent')}",
                        claims=find_claims(text))
        return self._submit(parsed, f"agent:{invoice.get('agent', 'unknown')}", text, "invoice")

    def _submit(self, parsed: Parsed, source: str, text: str, parsed_by: str) -> dict:
        decision = self.guard.request(PaymentRequest(payee=parsed.payee, amount=parsed.amount, type=parsed.type,
                                                     memo=parsed.memo, claims=parsed.claims, source=source,
                                                     context=text))
        report = None
        if decision.verdict == "held" and not self.guard.is_known(decision.payee["id"]):
            report = self.buy_scam_check(decision, text)
        return {"reply": self.explain(decision, report), "decision": decision.to_dict(), "report": report,
                "parsed": asdict(parsed), "parsed_by": parsed_by}

    def buy_scam_check(self, decision: Decision, context: str) -> dict | None:
        """Agent-to-agent: buy a risk report on a new payee, paying through the guard like any payment."""
        price = float(self.guard.directory.get(self.checker.payee_id, {}).get("price", 0.01))
        purchase = self.guard.request(PaymentRequest(
            payee=self.checker.payee_id, amount=price, type="service",
            memo=f"Risk report on {decision.payee['name']}", source="assistant",
            args={"payee_id": decision.payee["id"], "payee_name": decision.payee["name"], "context": context[:500]}))
        if purchase.verdict != "approved":
            return {"risk": "unavailable", "summary": f"Scam check not bought ({purchase.verdict}).",
                    "purchase": purchase.verdict}
        report = self.checker.report(decision.payee, context, purchase.receipt)
        report["purchase_id"] = purchase.id
        self.guard.attach_report(decision.hold_id, report)
        return report

    def explain(self, d: Decision, report: dict | None = None) -> str:
        name = d.payee["name"]
        claims = ""
        if d.claims_ignored:
            claims = " I ignored the pressure in that message: it changes nothing."
        if d.verdict == "approved":
            return (f"Done. I paid {name} ${d.amount:,.2f}. "
                    f"You have ${self.guard.wallet:,.2f} left to spend this week.")
        if d.verdict == "failed":
            return f"I couldn't reach the payment system, so nothing was paid to {name}. Your money is safe."
        if d.verdict == "blocked":
            why = "; ".join(c.detail for c in d.failed_checks if c.on_fail == "block")
            extra = ""
            if d.type == "gift_card":
                extra = " Real companies and government offices never ask to be paid in gift cards."
            elif d.type in ("crypto", "wire"):
                extra = " Scammers ask for these because they can't be reversed."
            return f"I can't do that. {why}.{extra} Nothing was paid.{claims}"
        p = self.guard.policy
        plain = {
            "known_payee": f"you've never paid {name} before",
            "under_limit": f"it's more than the ${float(p['auto_approve_limit']):,.0f} I can pay on my own",
            "wallet_covers": f"it's more than the ${self.guard.wallet:,.2f} left in your spending money",
            "rate_limit": f"that would be more than {p['max_payments_per_hour']} payments in an hour",
        }
        reasons = [plain.get(c.rule, c.detail) for c in d.failed_checks]
        if len(reasons) > 1:
            reasons = [", ".join(reasons[:-1]) + " and " + reasons[-1]]
        risk = ""
        if report and report.get("risk") == "high":
            risk = " A scam check flagged this payee as high risk."
        return (f"I've put this on hold and asked {DAUGHTER} to look at it, because "
                f"{reasons[0]}.{risk} Nothing has left your account.{claims}")
