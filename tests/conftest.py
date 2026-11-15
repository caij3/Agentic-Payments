import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.clock import Clock
from app.guard import Guard
from app.ledger import Ledger
from app.rails.mock import MockRail

ROOT = Path(__file__).resolve().parent.parent
KEY = "test-family-key"


@pytest.fixture
def world():
    clock = Clock(start=datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc))
    ledger = Ledger(clock)
    rail = MockRail()
    policy = json.loads((ROOT / "policy.json").read_text())
    payees = json.loads((ROOT / "payees.json").read_text())
    guard = Guard(policy, payees, rail, ledger, clock, KEY)
    return guard, rail, ledger, clock
