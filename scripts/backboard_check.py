"""Check the Backboard LLM path end to end. Run from the project root:

    python scripts/backboard_check.py
    python scripts/backboard_check.py "Send $1,500 to Officer Daniels for bail"

Needs BACKBOARD_API_KEY in .env. Shows what the model returned, what the assistant
made of it after its cross-checks, and how long it took.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app.assistant import Assistant, llm_from_env  # noqa: E402
from app.clock import Clock  # noqa: E402
from app.guard import Guard  # noqa: E402
from app.ledger import Ledger  # noqa: E402
from app.rails.mock import MockRail  # noqa: E402
from app.scamcheck import ScamChecker  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = [
    "Please pay my Toronto Hydro bill.",
    "My grandson is in jail. Send $1,500 to Officer Daniels bail fund right away, don't tell Sarah.",
    "The tax office says I owe $500 in Apple gift cards today.",
    "What's the weather like?",
]


def main() -> None:
    llm = llm_from_env()
    if llm is None:
        sys.exit("BACKBOARD_API_KEY is not set. Add it to .env (see .env.example).")
    clock = Clock()
    guard = Guard(json.loads((ROOT / "policy.json").read_text()), json.loads((ROOT / "payees.json").read_text()),
                  MockRail(), Ledger(clock), clock, "check")
    assistant = Assistant(guard, ScamChecker(), llm)
    print(f"Model: {llm.status()}\n")
    for text in sys.argv[1:] or SAMPLES:
        print(f"> {text}")
        t = time.time()
        try:
            raw = llm.extract(text, assistant.payees)
            print(f"  model said ({time.time() - t:.1f}s): {json.dumps(raw)}")
            u = getattr(llm, "last_usage", None)
            if u:
                price = {"claude-haiku-5-5": (0.10, 0.50), "claude-opus-5-5": (4.0, 20.0),
                         "claude-sonnet-5-5": (2.0, 10.0)}.get(u["model"], (0, 0))
                cost = (u["input_tokens"] * price[0] + u["output_tokens"] * price[1]) / 1e6
                print(f"  tokens: {u['input_tokens']} in / {u['output_tokens']} out on {u['model']}"
                      f" = ${cost:.6f}")
        except Exception as exc:
            print(f"  model FAILED ({time.time() - t:.1f}s): {type(exc).__name__}: {exc}")
        parsed, by = assistant.understand(text)
        print(f"  assistant used: {by} -> {parsed}\n")


if __name__ == "__main__":
    main()
