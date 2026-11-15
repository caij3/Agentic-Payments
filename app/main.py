"""FastAPI web API for ScamGuard. State lives in memory and resets on restart."""
from __future__ import annotations

import hmac
import itertools
import json
import os
import secrets
import socket
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from .assistant import DAUGHTER, GRANDMA, Assistant, llm_from_env  # noqa: E402
from .clock import Clock  # noqa: E402
from .guard import Guard, GuardError, NotAuthorized  # noqa: E402
from .ledger import Ledger  # noqa: E402
from .rails.mock import MockRail  # noqa: E402
from .scamcheck import ScamChecker  # noqa: E402
from .scenarios import SCENARIOS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
DEMO_MODE = os.getenv("DEMO_MODE", "1").lower() in ("1", "true", "yes")
FAMILY_KEY = os.getenv("FAMILY_KEY") or f"{secrets.randbelow(10**6):06d}"   # the family PIN
print(f"\n  ScamGuard family PIN: {FAMILY_KEY}   (family page: /family)\n", flush=True)
RAIL = os.getenv("RAIL", "mock").lower()


def load_json(name: str):
    return json.loads((ROOT / name).read_text())


def make_rail():
    if RAIL == "qatom":
        from .rails.qatom import QatomRail
        return QatomRail()
    return MockRail()


class World:
    """Everything that resets on 'Start over'."""

    def __init__(self) -> None:
        self.clock = Clock()
        self.ledger = Ledger(self.clock)
        self.rail = make_rail()
        self.guard = Guard(load_json("policy.json"), load_json("payees.json"), self.rail, self.ledger,
                           self.clock, FAMILY_KEY)
        self.assistant = Assistant(self.guard, ScamChecker(), llm_from_env())
        self.chat: list[dict] = []
        self._ids = itertools.count(1)
        self.rail_status = "Practice rail: ready (no real money)" if RAIL != "qatom" else "Qatom: checking..."

    def say(self, who: str, text: str, **extra) -> dict:
        msg = {"id": next(self._ids), "who": who, "text": text,
               "ts": self.clock.now().isoformat(timespec="seconds"), **extra}
        self.chat.append(msg)
        return msg

    def run_step(self, who: str, payload) -> dict:
        if who == "grandma_ask":            # shown only: the assistant goes to the billing agent instead
            self.say("grandma", payload)
            return {}
        if who == "invoice":
            inv = payload
            self.say("agent", inv["text"], agent=inv.get("agent"), amount=inv.get("amount"))
            out = self.assistant.handle_invoice(inv)
            self._reply(out)
            return out
        return self.run_message(who, payload)

    def _reply(self, out: dict) -> None:
        d = out.get("decision")
        extra = {}
        if d:
            extra = {"verdict": d["verdict"], "decision_id": d["id"], "hold_id": d.get("hold_id"),
                     "claims_ignored": d["claims_ignored"], "parsed_by": out.get("parsed_by")}
        self.say("assistant", out["reply"], **extra)

    def run_message(self, who: str, text: str) -> dict:
        if who == "caller":
            self.say("caller", text)
            return {}
        self.say(who, text)
        out = self.assistant.handle(text, speaker=who)
        self._reply(out)
        return out


world = World()
app = FastAPI(title="ScamGuard", version="0.1.0")


# Wrong-PIN lockout: 5 misses in 10 minutes locks every family action for the rest of the window.
FAILS: list[float] = []
LOCK_MAX, LOCK_WINDOW = 5, 600


def family_gate() -> None:
    now = time.time()
    FAILS[:] = [t for t in FAILS if now - t < LOCK_WINDOW]
    if len(FAILS) >= LOCK_MAX:
        raise HTTPException(429, "Too many wrong PINs. Family actions are locked for 10 minutes.")


@app.exception_handler(NotAuthorized)
async def _unauth(_: Request, exc: NotAuthorized):
    FAILS.append(time.time())
    left = max(0, LOCK_MAX - len(FAILS))
    return JSONResponse({"detail": f"Wrong PIN. {left} tries left before a 10-minute lock."}, status_code=401)


@app.exception_handler(GuardError)
async def _guard_err(_: Request, exc: GuardError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


def demo_only() -> None:
    if not DEMO_MODE:
        raise HTTPException(404, "Not available outside demo mode")


# ---------------------------------------------------------------- models
class ChatIn(BaseModel):
    message: str


class ApproveIn(BaseModel):
    trust_payee: bool = False


class TopupIn(BaseModel):
    amount: float


class SkipIn(BaseModel):
    hours: float = 24


# ---------------------------------------------------------------- read
@app.get("/api/state")
def state():
    g = world.guard
    g.tick()
    snap = g.snapshot()
    llm = world.assistant.llm
    return {
        "now": world.clock.now().isoformat(timespec="seconds"),
        "demo_mode": DEMO_MODE,
        "names": {"grandma": GRANDMA, "daughter": DAUGHTER},
        "rail": {"name": world.rail.name, "status": world.rail_status},
        "assistant": {"llm": llm.status() if llm else "Built-in parser (no LLM key set)",
                      "last_llm_error": world.assistant.last_llm_error},
        "policy": {k: v for k, v in g.policy.items() if k != "starting_savings"},
        "payees": [{"id": p["id"], "name": p["name"], "known": p["id"] in g.known_payees,
                    "on_qatom": bool(p.get("qatom_item"))} for p in g.directory.values()],
        "scenarios": [{"id": k, "title": v["title"], "blurb": v["blurb"]} for k, v in SCENARIOS.items()],
        "chat": world.chat[-60:],
        **snap,
    }


@app.get("/api/rail/status")
def rail_status():
    world.rail_status = world.rail.status()
    return {"rail": world.rail.name, "status": world.rail_status}


def lan_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sk:
            sk.connect(("10.255.255.255", 1))     # no packet is sent; picks the outbound interface
            return sk.getsockname()[0]
    except OSError:
        return None


@app.get("/api/demo-config")
def demo_config(request: Request):
    demo_only()
    ip = lan_ip()
    port = request.url.port or 8000
    return {"family_key": FAMILY_KEY, "lan_url": f"http://{ip}:{port}/family" if ip else None}


# ---------------------------------------------------------------- grandma / assistant
@app.post("/api/chat")
def chat(body: ChatIn):
    text = body.message.strip()
    if not text:
        raise HTTPException(400, "Empty message")
    out = world.run_message("grandma", text[:500])
    return {"reply": out.get("reply"), "decision": out.get("decision"), "report": out.get("report")}


@app.post("/api/scenario/{sid}")
def scenario(sid: str):
    sc = SCENARIOS.get(sid)
    if sc is None:
        raise HTTPException(404, "No such scenario")
    world.say("system", f"Scenario: {sc['title']}")
    results = []
    for who, payload in sc["steps"]:
        results.append(world.run_step(who, payload))
    return {"scenario": sid, "decisions": [r.get("decision") for r in results if r.get("decision")]}


# ---------------------------------------------------------------- family
@app.post("/api/holds/{hold_id}/approve", dependencies=[Depends(family_gate)])
def approve(hold_id: str, body: ApproveIn | None = None, x_family_key: str | None = Header(default=None)):
    trust = bool(body and body.trust_payee)
    hold = world.guard.approve(hold_id, x_family_key, trust_payee=trust)
    name = hold.payee["name"]
    if hold.status == "paid":
        world.say("family", f"Approved ${hold.amount:,.2f} to {name}" + (" and trusted them" if trust else "") + ".")
        world.say("assistant", f"{DAUGHTER} approved it. I paid {name} ${hold.amount:,.2f}. "
                               f"You have ${world.guard.wallet:,.2f} left this week.", verdict="approved")
    else:
        world.say("assistant", f"{DAUGHTER} approved it, but the payment system failed, so nothing was paid.",
                  verdict="failed")
    return hold.to_dict()


@app.post("/api/holds/{hold_id}/deny", dependencies=[Depends(family_gate)])
def deny(hold_id: str, x_family_key: str | None = Header(default=None)):
    hold = world.guard.deny(hold_id, x_family_key)
    world.say("family", f"Denied ${hold.amount:,.2f} to {hold.payee['name']}.")
    world.say("assistant", f"{DAUGHTER} said no to the ${hold.amount:,.2f} payment to {hold.payee['name']}. "
                           f"Nothing was paid. If someone is pressuring you, call {DAUGHTER}.", verdict="denied")
    return hold.to_dict()


@app.post("/api/topup", dependencies=[Depends(family_gate)])
def topup(body: TopupIn, x_family_key: str | None = Header(default=None)):
    wallet = world.guard.topup(body.amount, x_family_key)
    world.say("family", f"Topped up the spending wallet by ${body.amount:,.2f}.")
    return {"wallet": wallet, "savings": world.guard.savings}


@app.get("/api/family/check", dependencies=[Depends(family_gate)])
def family_check(x_family_key: str | None = Header(default=None)):
    world.guard._check_key(x_family_key)
    return {"ok": True, "names": {"grandma": GRANDMA, "daughter": DAUGHTER}}


@app.post("/api/freeze", dependencies=[Depends(family_gate)])
def freeze(x_family_key: str | None = Header(default=None)):
    was = world.guard.frozen
    world.guard.freeze(x_family_key)
    if not was:
        world.say("family", "Froze all payments.")
        world.say("assistant", f"{DAUGHTER} has paused all payments for now. Nothing can be paid until "
                               f"{DAUGHTER} turns them back on. Your money is safe.", verdict="frozen")
    return {"frozen": True}


@app.post("/api/unfreeze", dependencies=[Depends(family_gate)])
def unfreeze(x_family_key: str | None = Header(default=None)):
    was = world.guard.frozen
    world.guard.unfreeze(x_family_key)
    if was:
        world.say("family", "Turned payments back on.")
    return {"frozen": False}


@app.get("/api/policy")
def get_policy():
    g = world.guard
    return {**{k: v for k, v in g.policy.items() if k != "starting_savings"}, "known_payees": sorted(g.known_payees)}


@app.patch("/api/policy", dependencies=[Depends(family_gate)])
def patch_policy(changes: dict, x_family_key: str | None = Header(default=None)):
    after = world.guard.update_policy(x_family_key, changes)
    world.say("family", "Changed the rules: " + ", ".join(
        f"{k.replace('_', ' ')} {v}" for k, v in changes.items() if v not in (None, [], {})))
    return after


# ---------------------------------------------------------------- demo controls
@app.post("/api/clock/skip")
def clock_skip(body: SkipIn | None = None):
    demo_only()
    hours = body.hours if body else 24
    before = {h.id for h in world.guard.holds.values() if h.status == "pending"}
    world.clock.skip(hours)
    world.guard.tick()
    world.say("system", f"Skipped ahead {hours:g} hours")
    for h in world.guard.holds.values():
        if h.id in before and h.status == "expired":
            world.say("assistant", f"Nobody answered about the ${h.amount:,.2f} payment to {h.payee['name']}, "
                                   f"so I cancelled it. Nothing was paid.", verdict="expired")
    return {"now": world.clock.now().isoformat(timespec="seconds")}


@app.post("/api/reset")
def reset():
    demo_only()
    global world
    world = World()
    FAILS.clear()
    if RAIL == "qatom":
        world.rail_status = world.rail.status()
    return {"ok": True}


# ---------------------------------------------------------------- the ScamCheck agent (seller side)
class ScamCheckIn(BaseModel):
    payee_id: str | None = None
    payee_name: str | None = None
    context: str | None = None


@app.post("/api/agents/scamcheck")
def scamcheck_agent(body: ScamCheckIn, x_scamcheck_key: str | None = Header(default=None)):
    """The second agent's own endpoint. On Qatom, the ScamCheck catalog item forwards here after
    payment settles. Set SCAMCHECK_SECRET and add it to the item's dispatch params so only Qatom can call it."""
    secret = os.getenv("SCAMCHECK_SECRET", "")
    if secret and not hmac.compare_digest(x_scamcheck_key or "", secret):
        raise HTTPException(401, "Bad ScamCheck key")
    payee = world.guard.resolve_payee(body.payee_id or body.payee_name or "")
    rep = ScamChecker().report(payee, body.context or "")
    return {k: rep[k] for k in ("risk", "summary", "signals", "payee", "payee_name", "source")}


# ---------------------------------------------------------------- pages
@app.get("/")
@app.get("/demo")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/family")
def family_page():
    return FileResponse(STATIC / "family.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
