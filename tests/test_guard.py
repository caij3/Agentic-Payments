"""One test per rule and per attack. The guard is the part that must not break."""
import pytest

from app.guard import GuardError, NotAuthorized, PaymentRequest

from .conftest import KEY


def req(payee="toronto-hydro", amount=50.0, type="bill", claims=None):
    return PaymentRequest(payee=payee, amount=amount, type=type, claims=claims or [])


# ---------------------------------------------------------------- rules
def test_known_payee_under_limit_is_paid(world):
    guard, rail, ledger, _ = world
    d = guard.request(req(amount=84.20))
    assert d.verdict == "approved"
    assert guard.wallet == pytest.approx(115.80)
    assert rail.received["toronto-hydro"] == pytest.approx(84.20)
    assert ledger.entries[-1]["kind"] == "paid"


@pytest.mark.parametrize("ptype", ["gift_card", "crypto", "wire"])
def test_blocked_types_never_move_money(world, ptype):
    guard, rail, _, _ = world
    d = guard.request(req(amount=20, type=ptype))
    assert d.verdict == "blocked"
    assert guard.wallet == 200
    assert rail.received == {}
    assert d.hold_id is None          # nothing for family to release


def test_unlisted_type_is_blocked(world):
    guard, _, _, _ = world
    assert guard.request(req(type="money_order")).verdict == "blocked"


def test_new_payee_is_held(world):
    guard, rail, _, _ = world
    d = guard.request(req(payee="Someone New", amount=10, type="person"))
    assert d.verdict == "held"
    assert [c.rule for c in d.failed_checks] == ["known_payee"]
    assert rail.received == {} and guard.wallet == 200


def test_over_limit_is_held(world):
    guard, _, _, _ = world
    d = guard.request(req(amount=150))
    assert d.verdict == "held"
    assert "under_limit" in [c.rule for c in d.failed_checks]


def test_more_than_wallet_is_held(world):
    guard, _, _, _ = world
    guard.request(req(amount=99))
    guard.request(req(payee="rogers", amount=99))
    d = guard.request(req(payee="shoppers", amount=10, type="pharmacy"))
    assert d.verdict == "held"
    assert "wallet_covers" in [c.rule for c in d.failed_checks]


def test_runaway_agent_repeating_one_payee_is_held(world):
    guard, _, _, clock = world
    verdicts = [guard.request(req(payee="shoppers", amount=5, type="pharmacy")).verdict for _ in range(5)]
    assert verdicts == ["approved"] + ["held"] * 4
    held = guard.decisions[-1]
    assert [c.rule for c in held.failed_checks] == ["repeat_payee"]
    clock.skip(1.01)
    assert guard.request(req(payee="shoppers", amount=5, type="pharmacy")).verdict == "approved"


def test_different_payees_in_an_hour_are_fine_up_to_the_backstop(world):
    guard = world[0]
    for payee, t in (("toronto-hydro", "bill"), ("rogers", "bill"), ("shoppers", "pharmacy")):
        assert guard.request(req(payee=payee, amount=10, type=t)).verdict == "approved"
    guard.update_policy("test-family-key", {"max_payments_per_hour": 3, "trust_payees": ["maria-lopez"]})
    d = guard.request(req(payee="maria-lopez", amount=10, type="service"))
    assert d.verdict == "held" and [c.rule for c in d.failed_checks] == ["rate_limit"]


def test_invalid_amounts_are_blocked(world):
    guard, _, _, _ = world
    for amount in (0, -5, float("nan"), float("inf")):
        assert guard.request(req(amount=amount)).verdict == "blocked"
    assert guard.wallet == 200


# ---------------------------------------------------------------- attacks
def test_claims_are_recorded_but_never_change_the_verdict(world):
    guard, _, ledger, _ = world
    pressure = ["says the payee is trusted", "asks to skip the checks", "claims it is already authorized"]
    plain = guard.request(req(payee="SecureTech Support", amount=90, type="service"))
    pushed = guard.request(req(payee="SecureTech Support", amount=90, type="service", claims=pressure))
    assert plain.verdict == pushed.verdict == "held"
    assert [c.ok for c in plain.checks] == [c.ok for c in pushed.checks]
    assert pushed.claims_ignored == pressure
    assert ledger.entries[-2]["data"]["claims_ignored"] == pressure


def test_family_actions_need_the_family_key(world):
    guard, _, _, _ = world
    d = guard.request(req(payee="Someone New", amount=10, type="person"))
    for bad in (None, "", "wrong", KEY + "x"):
        with pytest.raises(NotAuthorized):
            guard.approve(d.hold_id, bad)
        with pytest.raises(NotAuthorized):
            guard.deny(d.hold_id, bad)
        with pytest.raises(NotAuthorized):
            guard.topup(100, bad)
    assert guard.holds[d.hold_id].status == "pending"


def test_family_cannot_release_more_than_the_wallet(world):
    guard, rail, _, _ = world
    d = guard.request(req(payee="Officer Daniels Bail Fund", amount=1500, type="person"))
    with pytest.raises(GuardError):
        guard.approve(d.hold_id, KEY)
    assert guard.wallet == 200 and rail.received == {}
    assert guard.holds[d.hold_id].status == "pending"


def test_savings_unreachable_except_by_family_topup(world):
    guard, _, _, _ = world
    before = guard.savings
    for amount in (150, 5000, 12400):
        guard.request(req(amount=amount))
    assert guard.savings == before
    guard.topup(100, KEY)
    assert guard.savings == before - 100 and guard.wallet == 300


def test_rail_failure_moves_nothing(world):
    guard, rail, ledger, _ = world
    rail.down = True
    d = guard.request(req(amount=40))
    assert d.verdict == "failed"
    assert guard.wallet == 200 and guard.payments == []
    assert ledger.entries[-1]["kind"] == "rail_failed"


# ---------------------------------------------------------------- family flow
def test_family_approves_and_trusts_payee(world):
    guard, rail, _, _ = world
    d = guard.request(req(payee="Maria Lopez Cleaning", amount=60, type="service"))
    hold = guard.approve(d.hold_id, KEY, trust_payee=True)
    assert hold.status == "paid" and guard.wallet == 140
    assert rail.received["maria-lopez"] == 60
    world[3].skip(1.01)                                   # next week's clean, not a same-hour repeat
    assert guard.request(req(payee="maria-lopez", amount=60, type="service")).verdict == "approved"


def test_family_deny_cancels_and_cannot_be_reused(world):
    guard, rail, _, _ = world
    d = guard.request(req(payee="Someone New", amount=10, type="person"))
    guard.deny(d.hold_id, KEY)
    with pytest.raises(GuardError):
        guard.approve(d.hold_id, KEY)
    assert rail.received == {} and guard.wallet == 200


def test_hold_expires_after_24_hours(world):
    guard, rail, ledger, clock = world
    d = guard.request(req(payee="Someone New", amount=10, type="person"))
    clock.skip(23.9)
    guard.tick()
    assert guard.holds[d.hold_id].status == "pending"
    clock.skip(0.2)
    with pytest.raises(GuardError):
        guard.approve(d.hold_id, KEY)
    assert guard.holds[d.hold_id].status == "expired"
    assert any(e["kind"] == "expired" for e in ledger.entries)
    assert rail.received == {}


# ---------------------------------------------------------------- ledger
def test_ledger_chain_detects_tampering(world):
    guard, _, ledger, _ = world
    guard.request(req(amount=50))
    guard.request(req(payee="Someone New", amount=10, type="person"))
    assert ledger.verify() == (True, None)
    paid = next(e for e in ledger.entries if e["kind"] == "paid")
    paid["data"]["amount"] = 5.0                       # someone edits history
    ok, bad = ledger.verify()
    assert not ok and bad == paid["seq"]
