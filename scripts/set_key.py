"""Save a secret into .env without showing it on screen. Run from the project root:

    .venv/bin/python scripts/set_key.py BACKBOARD_API_KEY

Paste the value at the prompt (it stays hidden) and press Enter. The value is written to the
NAME= line in .env (git-ignored) and never printed.
"""
from __future__ import annotations

import getpass
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
ALLOWED = {"PRESENTER_KEY", "ANTHROPIC_API_KEY", "BACKBOARD_API_KEY", "QATOM_CLIENT_ID", "QATOM_CLIENT_SECRET", "SCAMCHECK_SECRET", "FAMILY_KEY"}


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--visible"]
    name = args[0] if args else "BACKBOARD_API_KEY"
    if name not in ALLOWED:
        sys.exit(f"Unknown setting {name}. Use one of: {', '.join(sorted(ALLOWED))}")
    if "--visible" in sys.argv:   # some terminals block pasting into a hidden prompt
        value = input(f"Paste your {name} and press Enter: ")
    else:
        value = getpass.getpass(f"Paste your {name} and press Enter (it stays hidden): ")
    value = value.strip().strip('"').strip("'")
    if not value:
        sys.exit("Nothing pasted. Run it again.")
    if any(c.isspace() for c in value):
        sys.exit("That has spaces or line breaks in it, so it's probably not the key. Copy just the key and run it again.")
    if not ENV.exists():
        example = ROOT / ".env.example"
        ENV.write_text(example.read_text() if example.exists() else "")
    text = ENV.read_text()
    line = f"{name}={value}"
    pattern = re.compile(rf"^#?\s*{re.escape(name)}=.*$", re.M)
    text = pattern.sub(line, text, count=1) if pattern.search(text) else text.rstrip("\n") + f"\n{line}\n"
    ENV.write_text(text)
    os.chmod(ENV, 0o600)
    print(f"Saved {name} to .env ({len(value)} characters, ends in ...{value[-4:]}). Restart the server to use it.")


if __name__ == "__main__":
    main()
