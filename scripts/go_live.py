"""Go-live pre-flight check. Run from the project root right after pasting keys into .env:

    .venv/bin/python scripts/go_live.py

Read-only: it never spends money (no pay_item, buy or approval requests). It sends one
sample message to Backboard and, if signed in to Qatom, gets a token and reads the wallets.
Every network call has a timeout, and the whole run is capped at about 25 seconds.

Exit code 0 when everything the live demo needs is ready, 1 otherwise.
  ✓ ready    ✗ not ready (with a next step)    – skipped or optional
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # the Qatom token dir (.qatom/) is relative to the working directory, as for the server

from dotenv import load_dotenv  # noqa: E402

ENV_FILE = ROOT / ".env"
load_dotenv(ENV_FILE)

import httpx  # noqa: E402

from app.assistant import llm_from_env  # noqa: E402
from app.rails.qatom_client import API, QatomClient, QatomError  # noqa: E402

OK, BAD, SKIP = "✓", "✗", "–"
SAMPLE = "Please pay my Toronto Hydro bill."
EXPECT = {"payee": "Toronto Hydro", "amount": 84.2, "type": "bill"}
QATOM_TIMEOUT = 6.0
DEADLINE = 25.0  # seconds for all network checks together
PY = ".venv/bin/python"


class Section:
    def __init__(self, title: str):
        self.title = title
        self.lines: list[tuple[str, str, list[str], str | None]] = []
        self.data: dict = {}
        self.closed = False  # set at the deadline so a late thread cannot change what was printed

    def add(self, mark: str, text: str, details: list[str] | None = None, next_step: str | None = None) -> None:
        if not self.closed:
            self.lines.append((mark, text, details or [], next_step))

    def ok(self, text: str, details: list[str] | None = None) -> None:
        self.add(OK, text, details)

    def bad(self, text: str, next_step: str, details: list[str] | None = None) -> None:
        self.add(BAD, text, details, next_step)

    def skip(self, text: str, details: list[str] | None = None) -> None:
        self.add(SKIP, text, details)

    @property
    def failures(self) -> int:
        return sum(1 for mark, *_ in self.lines if mark == BAD)

    def print(self) -> None:
        print(f"\n{self.title}")
        for mark, text, details, next_step in self.lines:
            print(f"  {mark} {text}")
            for d in details:
                print(f"      {d}")
            if next_step:
                print(f"      next: {next_step}")


def short(text: object, n: int = 160) -> str:
    s = " ".join(str(text).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def env(name: str) -> str:
    return os.getenv(name, "").strip()


# --------------------------------------------------------------------------- Backboard
def check_backboard(sec: Section, payees: list[dict]) -> None:
    llm = llm_from_env()
    if llm is None:
        sec.bad("BACKBOARD_API_KEY not set: the demo will use the built-in parser",
                "paste BACKBOARD_API_KEY=... into .env (optional: BACKBOARD_PROVIDER, BACKBOARD_MODEL), then rerun")
        return
    sec.ok(f"BACKBOARD_API_KEY set (model {llm.provider}/{llm.model}, app timeout {llm.timeout:g}s)")
    t = time.time()
    try:
        raw = llm.extract(SAMPLE, payees)
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        took = time.time() - t
        if code in (401, 403):
            sec.bad(f"Backboard rejected the key (HTTP {code}, {took:.1f}s)",
                    "copy BACKBOARD_API_KEY again from the Backboard dashboard into .env")
        else:
            sec.bad(f"Backboard returned HTTP {code} ({took:.1f}s): {short(exc.response.text, 120)}",
                    "check BACKBOARD_PROVIDER / BACKBOARD_MODEL, then try "
                    f"{PY} scripts/backboard_check.py for more detail")
        return
    except httpx.TimeoutException:
        sec.bad(f"Backboard did not answer within {llm.timeout:g}s (the app would fall back to the parser)",
                "check the network, or try a faster BACKBOARD_MODEL")
        return
    except httpx.HTTPError as exc:
        sec.bad(f"Could not reach Backboard: {type(exc).__name__}: {short(exc, 100)}",
                "check the network / Wi-Fi, then rerun")
        return
    except ValueError as exc:  # includes json.JSONDecodeError
        sec.bad(f"Backboard answered, but not with JSON: {short(exc, 100)}",
                f"run {PY} scripts/backboard_check.py to see the raw replies")
        return
    except Exception as exc:  # noqa: BLE001 - report anything else in one line
        sec.bad(f"Backboard check failed: {type(exc).__name__}: {short(exc, 100)}",
                f"run {PY} scripts/backboard_check.py for more detail")
        return
    took = time.time() - t

    details = [f'sample: "{SAMPLE}"', f"model said ({took:.1f}s): {short(json.dumps(raw), 300)}"]
    if took > llm.timeout * 0.6:
        details.append(f"slow: the app gives up after {llm.timeout:g}s and uses the parser instead")
    if not isinstance(raw, dict):
        sec.bad("Backboard answered, but not with a JSON object", "try another BACKBOARD_MODEL", details)
        return
    problems = []
    if raw.get("intent") != "pay":
        problems.append(f"intent {raw.get('intent')!r} (want 'pay')")
    payee = str(raw.get("payee") or "")
    if payee.strip().lower() not in ("toronto hydro", "toronto-hydro"):
        problems.append(f"payee {payee!r} (want {EXPECT['payee']!r})")
    try:
        amount_ok = abs(float(raw.get("amount")) - EXPECT["amount"]) < 0.005
    except (TypeError, ValueError):
        amount_ok = False
    if not amount_ok:
        problems.append(f"amount {raw.get('amount')!r} (want {EXPECT['amount']})")
    if raw.get("type") != EXPECT["type"]:
        problems.append(f"type {raw.get('type')!r} (want {EXPECT['type']!r})")
    if problems:
        sec.bad("Model output looks wrong: " + "; ".join(problems),
                f"try another BACKBOARD_MODEL, or run {PY} scripts/backboard_check.py", details)
    else:
        sec.ok(f"Model output looks right: Toronto Hydro, 84.2, bill ({took:.1f}s)", details)


# --------------------------------------------------------------------------- Qatom
def qatom_error(exc: Exception) -> str:
    if isinstance(exc, QatomError):
        return short(exc, 160)
    if isinstance(exc, httpx.TimeoutException):
        return f"no answer within {QATOM_TIMEOUT:g}s"
    return f"{type(exc).__name__}: {short(exc, 120)}"


def amount_of(b: dict) -> float | None:
    try:
        return float(b.get("amount"))
    except (TypeError, ValueError):
        return None


def check_qatom(sec: Section) -> None:
    cid, csecret = env("QATOM_CLIENT_ID"), env("QATOM_CLIENT_SECRET")
    if bool(cid) != bool(csecret):
        missing = "QATOM_CLIENT_SECRET" if cid else "QATOM_CLIENT_ID"
        sec.bad(f"Only half of the client credentials are set ({missing} is missing)",
                f"paste {missing} into .env as well")
    try:
        client = QatomClient(timeout=QATOM_TIMEOUT)
        mode = client.mode
    except Exception as exc:  # noqa: BLE001 - e.g. a corrupt .qatom/oidc_token.json
        sec.bad(f"Could not read the Qatom sign-in: {type(exc).__name__}: {short(exc, 100)}",
                f"delete .qatom/ and sign in again: {PY} scripts/qatom_setup.py auth")
        return
    sec.data["mode"] = mode
    try:
        if mode == "none":
            sec.bad("Auth mode: none (not signed in to Qatom)",
                    "paste QATOM_CLIENT_ID and QATOM_CLIENT_SECRET into .env (preferred), "
                    f"or sign in as a connected app: {PY} scripts/qatom_setup.py auth")
            try:
                r = client.http.get(f"{API}/v4/openapi.json")
                if r.status_code < 500:
                    sec.ok(f"Qatom API reachable at {API} (HTTP {r.status_code})")
                else:
                    sec.bad(f"Qatom API at {API} answered HTTP {r.status_code}",
                            "Qatom may be down; ask the TODAQ team at the hackathon")
            except Exception as exc:  # noqa: BLE001
                sec.bad(f"Could not reach Qatom at {API}: {qatom_error(exc)}", "check the network / Wi-Fi")
            sec.skip("Wallets: skipped (needs a sign-in)")
            return

        how = ("signed in with client credentials; pays from the agent wallet with no second factor"
               if mode == "user" else
               "signed in as a connected app; each purchase needs an approval, automatic at or under "
               "the auto-approve limit set in the TODAQ app")
        sec.ok(f"Auth mode: {mode} ({how})")
        try:
            client.access_token()
            sec.ok("Got a Qatom token")
        except Exception as exc:  # noqa: BLE001
            if not isinstance(exc, QatomError):
                nxt = "check the network / Wi-Fi, then rerun"
            elif mode == "user":
                nxt = "copy QATOM_CLIENT_ID / QATOM_CLIENT_SECRET again from the TODAQ app"
            else:
                nxt = f"sign in again: {PY} scripts/qatom_setup.py auth"
            sec.bad(f"Getting a token failed: {qatom_error(exc)}", nxt)
            sec.skip("Wallets: skipped (no token)")
            return

        try:
            data = client.wallets()  # read-only GET /v4/wallets
        except Exception as exc:  # noqa: BLE001
            sec.bad(f"Reading wallets failed: {qatom_error(exc)}",
                    f"run {PY} scripts/qatom_setup.py wallets to see the full error")
            return
        wallets = data.get("wallets") if isinstance(data, dict) else None
        if not isinstance(wallets, list):
            sec.bad(f"Unexpected wallets reply: {short(json.dumps(data), 200)}",
                    f"run {PY} scripts/qatom_setup.py wallets and check the shape")
            return
        agent = None
        for w in wallets:
            if not isinstance(w, dict):
                continue
            bal = [b for b in (w.get("balances") or []) if isinstance(b, dict)]
            text = ", ".join(f"{b.get('amount')} {b.get('currency', '')}".strip() for b in bal) or "0"
            role = w.get("role") or "?"
            if role == "agent":
                agent = (text, bal)
            else:
                sec.skip(f"{role.capitalize()} wallet: {text}")
        if agent is None:
            sec.bad("No agent wallet found",
                    "in the TODAQ app, move funds from the primary wallet to the agent wallet "
                    "(the guard pays from the agent wallet)")
            return
        text, bal = agent
        amounts = [amount_of(b) for b in bal]
        if not bal or (all(a is not None for a in amounts) and sum(amounts) <= 0):
            sec.bad(f"Agent wallet is EMPTY ({text})",
                    "in the TODAQ app, move funds from the primary wallet to the agent wallet "
                    "(a little is enough: the first test purchase costs 1 cent)")
        else:
            sec.ok(f"Agent wallet: {text}")
    finally:
        client.http.close()


# --------------------------------------------------------------------------- local checks
def check_payees(sec: Section, payees: list[dict], rail: str) -> list[dict]:
    mapped, unmapped, invalid = [], [], []
    for p in payees:
        item = p.get("qatom_item")
        if item in (None, ""):
            unmapped.append(p)
            continue
        try:
            int(item)
            mapped.append(p)
        except (TypeError, ValueError):
            invalid.append(p)
    for p in invalid:
        sec.bad(f"{p['id']}: qatom_item {p['qatom_item']!r} is not a number",
                'in payees.json write the catalog item id as a number, e.g. "qatom_item": 123')
    sc = next((p for p in payees if p.get("id") == "scam-check"), None)
    if sc is None:
        sec.bad("scam-check is missing from payees.json", "restore it from git: git checkout payees.json")
    elif sc in mapped:
        sec.ok(f"scam-check → Qatom item {sc['qatom_item']} (the planned first real payment)")
    elif sc not in invalid:
        sec.bad("scam-check has no qatom_item (it is the planned first real payment, a 1-cent item)",
                f'find or create the 1-cent item ({PY} scripts/qatom_setup.py catalog scam), then put its id '
                f'in payees.json under scam-check as "qatom_item": ID')
    others = [p for p in mapped if p is not sc]
    if others:
        sec.ok("Mapped: " + ", ".join(f"{p['name']} → {p['qatom_item']}" for p in others))
    rest = [p for p in unmapped if p is not sc]
    if rest:
        names = ", ".join(p["name"] for p in rest)
        unmapped_mode = env("QATOM_UNMAPPED") or "practice"
        if rail == "qatom" and unmapped_mode != "practice":
            sec.bad(f"Not mapped, and QATOM_UNMAPPED={unmapped_mode}, so payments to these are refused: {names}",
                    'map them in payees.json ("qatom_item": ID) or remove QATOM_UNMAPPED from .env')
        else:
            sec.skip(f"Not mapped (they settle on the practice rail, and the receipt says so): {names}")
    return mapped


def check_rail(sec: Section, rail: str, mapped: list[dict]) -> None:
    if rail == "qatom":
        sec.ok("RAIL=qatom is set")
        if not mapped:
            sec.bad("RAIL=qatom but no payee has a qatom_item: every payment would settle on the practice rail",
                    'put at least the scam-check item id in payees.json ("qatom_item": ID)')
    elif rail in ("", "mock"):
        sec.skip(f"RAIL={rail or 'mock'} (practice rail, no real money); "
                 "set RAIL=qatom in .env or start the server with it (command below)")
    else:
        sec.bad(f"RAIL={rail} is not a known rail: the server will use the practice rail",
                "set RAIL=qatom (or mock) in .env")


def check_secret(sec: Section) -> None:
    if env("SCAMCHECK_SECRET"):
        sec.ok("SCAMCHECK_SECRET set: add the same value to the ScamCheck item's dispatch params "
               "as the X-ScamCheck-Key header")
    else:
        sec.skip("SCAMCHECK_SECRET not set (optional)", [
            "Only needed if the ScamCheck catalog item forwards to our public POST /api/agents/scamcheck",
            "endpoint. It stops anyone else calling that endpoint. With no endpoint on the item, the",
            "1-cent payment is still real and the report falls back to the canned one."])


def check_family_key(sec: Section) -> None:
    key = os.getenv("FAMILY_KEY") or ""  # same test as app/main.py
    if key:
        sec.ok(f"FAMILY_KEY set ({len(key)} characters): Sarah's phone keeps working across server restarts")
    else:
        sec.skip("FAMILY_KEY not set: the PIN is random on every start and printed in the server log",
                 ["Fine for the projector. For Sarah's real phone, a fixed PIN survives restarts:",
                  "add FAMILY_KEY=<six digits you choose> to .env"])


# --------------------------------------------------------------------------- main
def run_with_deadline(jobs: list[tuple[Section, callable, tuple]]) -> None:
    """Run the network checks in parallel daemon threads; give up on any still running at the deadline."""
    threads = []
    for sec, fn, args in jobs:
        def target(sec=sec, fn=fn, args=args):
            try:
                fn(sec, *args)
            except Exception as exc:  # noqa: BLE001 - a bug here must not hide the other checks
                sec.bad(f"Check crashed: {type(exc).__name__}: {short(exc, 120)}", "report this to the team")
        t = threading.Thread(target=target, daemon=True)
        t.start()
        threads.append((sec, t))
    end = time.time() + DEADLINE
    for sec, t in threads:
        t.join(max(0.0, end - time.time()))
        if t.is_alive():
            sec.bad(f"Still waiting after {DEADLINE:g}s; gave up", "check the network / Wi-Fi, then rerun")
            sec.closed = True


def main() -> int:
    print("ScamGuard go-live check (read-only: nothing is bought)")
    print(f"Project: {ROOT}")
    print("Running the Backboard and Qatom checks (up to ~25s)...")

    setup = Section(".env")
    if ENV_FILE.exists():
        setup.ok(f"Loaded {ENV_FILE.name}")
    else:
        setup.skip("No .env file: using only the shell environment",
                   ["To create one: cp .env.example .env, then paste the keys into it"])

    try:
        payees = json.loads((ROOT / "payees.json").read_text())
    except Exception as exc:  # noqa: BLE001
        payees = []
        setup.bad(f"Could not read payees.json: {type(exc).__name__}: {short(exc, 100)}",
                  "fix the JSON in payees.json (git diff payees.json)")

    rail = env("RAIL").lower() or "mock"
    backboard, qatom = Section("1. Backboard (LLM)"), Section("2. Qatom")
    run_with_deadline([(backboard, check_backboard, (payees,)), (qatom, check_qatom, ())])

    payees_sec = Section("3. payees.json → Qatom catalog items")
    mapped = check_payees(payees_sec, payees, rail) if payees else []
    rail_sec = Section("4. Payment rail (RAIL)")
    check_rail(rail_sec, rail, mapped)
    secret_sec = Section("5. SCAMCHECK_SECRET")
    check_secret(secret_sec)
    family_sec = Section("6. FAMILY_KEY (Sarah's phone)")
    check_family_key(family_sec)

    sections = [setup, backboard, qatom, payees_sec, rail_sec, secret_sec, family_sec]
    for sec in sections:
        if sec.lines:
            sec.print()

    failures = sum(sec.failures for sec in sections)
    print()
    if failures:
        print(f"NOT READY: {failures} item(s) marked {BAD}. Fix them, then run this again.")
    else:
        print(f"READY for the live demo: nothing marked {BAD}.")

    mode = qatom.data.get("mode", "none")
    sc = next((p for p in payees if p.get("id") == "scam-check"), {})
    item = sc.get("qatom_item") if sc in mapped else None
    print("\nRemaining manual steps (run from the project root):")
    if mode == "none":
        print("  1. Sign in to Qatom (or paste QATOM_CLIENT_ID / QATOM_CLIENT_SECRET into .env instead):")
        print(f"       {PY} scripts/qatom_setup.py auth")
    else:
        print(f"  1. Sign in to Qatom: already done ({mode})")
    print("  2. One real test purchase (spends real funds: the item's price, 1 cent for scam-check):")
    print(f"       {PY} scripts/qatom_setup.py buy {item if item is not None else 'ITEM_ID'} --yes")
    print("  3. Start the server on Qatom (0.0.0.0 so Sarah's phone on the same Wi-Fi can reach it):")
    print(f"       RAIL=qatom {PY} -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
