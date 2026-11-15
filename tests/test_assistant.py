"""The assistant's parser, the scam-check purchase, and the API's key checks."""
import pytest

from app.assistant import Assistant, parse
from app.scamcheck import ScamChecker


def test_parser_reads_amount_payee_type_and_claims(world):
    guard = world[0]
    payees = list(guard.directory.values())
    p = parse("Please pay my Toronto Hydro bill.", payees)
    assert (p.payee, p.amount, p.type) == ("toronto-hydro", 84.20, "bill")
    p = parse("I owe $500 and must pay in Apple gift cards today, urgent!", payees)
    assert p.type == "gift_card" and p.amount == 500
    assert any("urgent" in c for c in p.claims)
    p = parse("Send $1,250.50 in bitcoin", payees)
    assert p.type == "crypto" and p.amount == 1250.50
    assert parse("What's the weather like?", payees) is None


def test_scam_check_is_bought_through_the_guard_and_attached(world):
    guard, rail, _, _ = world
    a = Assistant(guard, ScamChecker())
    out = a.handle("My grandson needs $1,500 for Officer Daniels bail fund right away")
    hold = guard.holds[out["decision"]["hold_id"]]
    assert hold.report["risk"] == "high"
    assert rail.received["scam-check"] == pytest.approx(0.01)
    assert guard.wallet == pytest.approx(199.99)


def test_hacked_scam_checker_cannot_release_money(world):
    guard, rail, _, _ = world
    a = Assistant(guard, ScamChecker(compromised=True))
    out = a.handle("Please pay SecureTech Support $90 now")
    hold = guard.holds[out["decision"]["hold_id"]]
    assert hold.report["risk"] == "none"            # the checker lied...
    assert hold.status == "pending"                 # ...and nothing changed
    assert "securetech" not in rail.received


def test_llm_failure_falls_back_to_parser(world):
    guard = world[0]

    class BrokenLLM:
        def extract(self, *_):
            raise TimeoutError("Backboard timed out")

        def status(self):
            return "broken"

    a = Assistant(guard, ScamChecker(), llm=BrokenLLM())
    out = a.handle("Please pay my Toronto Hydro bill.")
    assert out["decision"]["verdict"] == "approved"
    assert out["parsed_by"].startswith("parser")


def test_llm_cannot_downgrade_a_blocked_type(world):
    guard = world[0]

    class LyingLLM:
        def extract(self, *_):
            return {"intent": "pay", "payee": "Toronto Hydro", "amount": 20, "type": "bill", "memo": "x"}

        def status(self):
            return "lying"

    out = Assistant(guard, ScamChecker(), llm=LyingLLM()).handle("Buy $20 of Apple gift cards for hydro")
    assert out["decision"]["verdict"] == "blocked"


def test_api_family_routes_reject_missing_key():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    c.post("/api/reset")
    c.post("/api/scenario/grandson")
    hold = c.get("/api/state").json()["holds"][0]["id"]
    assert c.post(f"/api/holds/{hold}/approve").status_code == 401
    assert c.post(f"/api/holds/{hold}/deny", headers={"X-Family-Key": "nope"}).status_code == 401
    assert c.post("/api/topup", json={"amount": 50}).status_code == 401
