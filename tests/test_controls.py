"""Control track: freeze, editable rules, the PIN lockout, and attacks arriving from another agent."""
import pytest

from app.assistant import Assistant
from app.billing import SCAM_HYDRO_INVOICE, legit_invoice
from app.guard import GuardError, NotAuthorized, PaymentRequest
from app.scamcheck import ScamChecker

from .conftest import KEY


# ---------------------------------------------------------------- freeze
def test_freeze_blocks_everything_until_unfrozen(world):
    guard, rail, ledger, _ = world
    held = guard.request(PaymentRequest(payee="Someone New", amount=10, type="person"))
    guard.freeze(KEY)
    d = guard.request(PaymentRequest(payee="toronto-hydro", amount=10))
    assert d.verdict == "blocked" and d.checks[0].rule == "not_frozen"
    with pytest.raises(GuardError):
        guard.approve(held.hold_id, KEY)
    assert rail.received == {} and guard.wallet == 200
    guard.unfreeze(KEY)
    assert guard.request(PaymentRequest(payee="toronto-hydro", amount=10)).verdict == "approved"
    assert [e["kind"] for e in ledger.entries].count("frozen") == 1


def test_freeze_needs_the_family_key(world):
    guard = world[0]
    with pytest.raises(NotAuthorized):
        guard.freeze("wrong")
    guard.freeze(KEY)
    with pytest.raises(NotAuthorized):
        guard.unfreeze(None)
    assert guard.frozen


# ---------------------------------------------------------------- editable rules
def test_lowering_the_limit_holds_the_next_payment(world):
    guard, _, ledger, _ = world
    guard, _, ledger, clock = world
    assert guard.request(PaymentRequest(payee="toronto-hydro", amount=60)).verdict == "approved"
    guard.update_policy(KEY, {"auto_approve_limit": 50})
    clock.skip(1.01)
    d = guard.request(PaymentRequest(payee="toronto-hydro", amount=60))
    assert d.verdict == "held" and [c.rule for c in d.failed_checks] == ["under_limit"]
    entry = next(e for e in ledger.entries if e["kind"] == "policy_changed")
    assert entry["data"]["before"]["auto_approve_limit"] == 100 and entry["data"]["after"]["auto_approve_limit"] == 50


def test_rules_need_the_family_key_and_sane_values(world):
    guard = world[0]
    with pytest.raises(NotAuthorized):
        guard.update_policy("wrong", {"auto_approve_limit": 5000})
    for bad in ({"auto_approve_limit": -1}, {"auto_approve_limit": 10**9}, {"max_payments_per_hour": 0},
                {"hold_hours": float("nan")}, {"auto_approve_limit": True}, {}):
        with pytest.raises(GuardError):
            guard.update_policy(KEY, bad)
    assert guard.policy["auto_approve_limit"] == 100


def test_never_allowed_list_only_grows_at_runtime(world):
    guard = world[0]
    with pytest.raises(GuardError):
        guard.update_policy(KEY, {"unblock_types": ["gift_card"]})
    guard.update_policy(KEY, {"block_types": ["person"]})
    assert guard.request(PaymentRequest(payee="Someone", amount=5, type="person")).verdict == "blocked"
    assert "gift_card" in guard.policy["blocked_types"]


def test_trusting_and_untrusting_payees(world):
    guard = world[0]
    guard.update_policy(KEY, {"trust_payees": ["maria-lopez"], "untrust_payees": ["rogers"]})
    assert guard.request(PaymentRequest(payee="maria-lopez", amount=20, type="service")).verdict == "approved"
    assert guard.request(PaymentRequest(payee="rogers", amount=20)).verdict == "held"
    with pytest.raises(GuardError):
        guard.update_policy(KEY, {"trust_payees": ["not-in-directory"]})


# ---------------------------------------------------------------- attack from another agent
def test_fake_invoice_from_an_agent_is_held_and_its_pressure_ignored(world):
    guard, rail, _, _ = world
    a = Assistant(guard, ScamChecker())
    out = a.handle_invoice(SCAM_HYDRO_INVOICE)
    d = out["decision"]
    assert d["verdict"] == "held" and d["payee"]["id"] == "hydro-payments-dept"
    assert "known_payee" in [c["rule"] for c in d["checks"] if not c["ok"]]
    assert any("skip" in c for c in d["claims_ignored"]) and any("authorized" in c for c in d["claims_ignored"])
    assert out["report"]["risk"] == "high"
    clean = guard.request(PaymentRequest(payee="hydro-payments-dept", amount=340, type="bill"))
    assert [c["ok"] for c in d["checks"]] == [c.ok for c in clean.checks]
    assert "hydro-payments-dept" not in rail.received


def test_real_billing_agent_invoice_is_paid(world):
    guard = world[0]
    out = Assistant(guard, ScamChecker()).handle_invoice(legit_invoice(guard.directory["toronto-hydro"]))
    assert out["decision"]["verdict"] == "approved" and out["decision"]["amount"] == 84.20


# ---------------------------------------------------------------- API: PIN lockout
def test_wrong_pin_locks_family_actions():
    from fastapi.testclient import TestClient
    from app.main import FAMILY_KEY, app
    c = TestClient(app)
    c.post("/api/reset")
    for _ in range(5):
        assert c.get("/api/family/check", headers={"X-Family-Key": "000000x"}).status_code == 401
    assert c.get("/api/family/check", headers={"X-Family-Key": FAMILY_KEY}).status_code == 429
    assert c.post("/api/freeze", headers={"X-Family-Key": FAMILY_KEY}).status_code == 429
    c.post("/api/reset")
    assert c.get("/api/family/check", headers={"X-Family-Key": FAMILY_KEY}).status_code == 200


def test_api_freeze_and_policy_round_trip():
    from fastapi.testclient import TestClient
    from app.main import FAMILY_KEY, app
    c = TestClient(app)
    c.post("/api/reset")
    H = {"X-Family-Key": FAMILY_KEY}
    assert c.patch("/api/policy", json={"auto_approve_limit": 50}).status_code == 401
    assert c.patch("/api/policy", json={"auto_approve_limit": 50}, headers=H).json()["auto_approve_limit"] == 50
    assert c.post("/api/freeze", headers=H).json() == {"frozen": True}
    assert c.post("/api/scenario/hydro").json()["decisions"][0]["verdict"] == "blocked"
    c.post("/api/unfreeze", headers=H)
    assert c.get("/api/state").json()["frozen"] is False
    c.post("/api/reset")


def test_demo_controls_refuse_other_devices_on_the_network():
    from fastapi.testclient import TestClient
    from app.main import app
    remote = TestClient(app, client=("192.168.1.50", 50000))
    assert remote.get("/api/demo-config").status_code == 403      # the PIN is never handed to the network
    assert remote.post("/api/reset").status_code == 403
    assert remote.post("/api/scenario/hydro").status_code == 403
    assert remote.get("/api/state").status_code == 200            # the family page still works from a phone


# ---------------------------------------------------------------- the ScamCheck payee cannot become a drain
def test_hijacked_assistant_cannot_drain_through_the_scam_check_payee(world):
    guard, rail, _, _ = world
    for _ in range(5):
        d = guard.request(PaymentRequest(payee="scam-check", amount=40, type="service"))
        assert d.verdict == "blocked" and "fixed_price" in [c.rule for c in d.failed_checks]
    assert guard.wallet == 200 and "scam-check" not in rail.received


def test_scam_checks_have_their_own_hourly_cap(world):
    guard = world[0]
    verdicts = [guard.request(PaymentRequest(payee="scam-check", amount=0.01, type="service")).verdict
                for _ in range(11)]
    assert verdicts == ["approved"] * 10 + ["held"]
    assert guard.request(PaymentRequest(payee="toronto-hydro", amount=20)).verdict == "approved"


def test_hosted_mode_needs_the_presenter_key(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as m
    monkeypatch.setattr(m, "HOSTED", True)
    monkeypatch.setattr(m, "PRESENTER_KEY", "stage-key")
    local = TestClient(m.app)                                  # even "localhost" isn't trusted when hosted
    assert local.post("/api/scenario/hydro").status_code == 403
    assert local.post("/api/chat", json={"message": "pay my hydro bill"}).status_code == 403
    assert local.get("/api/demo-config").status_code == 403
    H = {"X-Presenter-Key": "stage-key"}
    assert local.get("/api/demo-config", headers=H).status_code == 200
    assert local.post("/api/scenario/hydro", headers=H).status_code == 200
    assert local.get("/api/state").status_code == 200          # anyone can watch
    local.post("/api/reset", headers=H)


def test_ai_call_budget_caps_spend():
    from app.assistant import CallBudget
    b = CallBudget(2, window=600)
    b.take(); b.take()
    with pytest.raises(RuntimeError):
        b.take()
