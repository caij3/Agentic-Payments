"""The Qatom rail against a fake Qatom client: no network, no real money."""
import json
from datetime import datetime, timezone

import pytest

from app.assistant import Assistant
from app.clock import Clock
from app.guard import Guard, PaymentRequest
from app.ledger import Ledger
from app.rails.qatom import QatomRail
from app.rails.qatom_client import QatomError
from app.scamcheck import ScamChecker

from .conftest import ROOT


class FakeQatom:
    mode = "user"

    def __init__(self, fail=None, body=None):
        self.fail = fail
        self.body = body if body is not None else {"ok": True}
        self.calls = []

    def pay_item(self, item_id, arguments):
        self.calls.append((item_id, arguments))
        if self.fail:
            raise QatomError(self.fail, status=403)
        return {"tx_id": f"tx_{len(self.calls)}", "charged": "0.010", "currency": "USD-TDN", "body": self.body}

    def agent_balance(self):
        return "1.000 USD-TDN"


def make(fake, items=None):
    clock = Clock(start=datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc))
    payees = json.loads((ROOT / "payees.json").read_text())
    for p in payees:
        if items and p["id"] in items:
            p["qatom_item"] = items[p["id"]]
            p["qatom_pass_args"] = p["id"] == "scam-check"
    rail = QatomRail(client=fake)
    guard = Guard(json.loads((ROOT / "policy.json").read_text()), payees, rail, Ledger(clock), clock, "k")
    return guard, rail


def test_mapped_payee_settles_on_qatom_with_receipt():
    fake = FakeQatom()
    guard, _ = make(fake, {"toronto-hydro": 101})
    d = guard.request(PaymentRequest(payee="toronto-hydro", amount=84.20))
    assert d.verdict == "approved"
    assert d.receipt["rail"] == "qatom" and d.receipt["tx_id"] == "tx_1"
    assert d.receipt["settled"] == "0.010 USD-TDN"
    assert fake.calls == [(101, {})]


def test_unmapped_payee_settles_on_practice_and_says_so():
    guard, _ = make(FakeQatom())
    d = guard.request(PaymentRequest(payee="rogers", amount=20))
    assert d.verdict == "approved" and d.receipt["rail"].startswith("practice")


def test_qatom_refusal_moves_nothing():
    guard, _ = make(FakeQatom(fail="approval_required"), {"toronto-hydro": 101})
    d = guard.request(PaymentRequest(payee="toronto-hydro", amount=50))
    assert d.verdict == "failed" and guard.wallet == 200
    assert guard.ledger.entries[-1]["kind"] == "rail_failed"


def test_scam_check_bought_on_qatom_uses_the_sellers_report():
    report = {"risk": "high", "summary": "From the real seller", "signals": ["x"]}
    fake = FakeQatom(body=report)
    guard, _ = make(fake, {"scam-check": 777})
    out = Assistant(guard, ScamChecker()).handle("Send $1,500 to Officer Daniels bail fund")
    hold = guard.holds[out["decision"]["hold_id"]]
    assert hold.report["summary"] == "From the real seller" and hold.report["tx_id"] == "tx_1"
    item, args = fake.calls[0]
    assert item == 777 and args["payee_id"] == "daniels-bail"
    assert hold.status == "pending"


def test_scamcheck_endpoint_serves_reports(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.post("/api/agents/scamcheck", json={"payee_name": "Officer Daniels Bail Fund"})
    assert r.status_code == 200 and r.json()["risk"] == "high"
    monkeypatch.setenv("SCAMCHECK_SECRET", "s3")
    assert c.post("/api/agents/scamcheck", json={"payee_id": "maria-lopez"}).status_code == 401
    r = c.post("/api/agents/scamcheck", json={"payee_id": "maria-lopez"}, headers={"X-ScamCheck-Key": "s3"})
    assert r.json()["risk"] == "low"


@pytest.mark.parametrize("status", ["Qatom (user token): agent wallet 1.000 USD-TDN"])
def test_status_line(status):
    _, rail = make(FakeQatom())
    assert rail.status() == status


def test_checkout_reply_parsing():
    from app.rails.qatom_client import parse_checkout
    ok = parse_checkout({"content": [{"type": "text", "text": "Purchased"}],
                         "structuredContent": {"purchase": {"transaction_id": "t-1", "amount_charged": 0.001,
                                                            "currency": "USD-TDN"}, "response": {"risk": "low"}}})
    assert ok["tx_id"] == "t-1" and ok["charged"] == "0.001" and ok["body"] == {"risk": "low"}
    with pytest.raises(QatomError) as e:
        parse_checkout({"content": [{"type": "text", "text": "Approve this purchase in your TODAQ app"}],
                        "structuredContent": {"approval_id": "aar_1", "approve_url": "https://x/approve"}})
    assert "https://x/approve" in str(e.value)
    with pytest.raises(QatomError):
        parse_checkout({"isError": True, "content": [{"type": "text", "text": "Insufficient funds"}]})


def test_unmapped_args_are_not_sent_to_items_that_do_not_declare_them():
    fake = FakeQatom()
    guard, _ = make(fake, {"toronto-hydro": 101})
    guard.request(PaymentRequest(payee="toronto-hydro", amount=10, args={"secret": "x"}))
    assert fake.calls == [(101, {})]
