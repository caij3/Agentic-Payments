"""Qatom setup helper. Run from the project root:

    python scripts/qatom_setup.py token        # check QATOM_CLIENT_ID/SECRET from .env (preferred)
    python scripts/qatom_setup.py auth         # or: sign in in the browser as a connected app (OIDC)
    python scripts/qatom_setup.py wallets      # primary and agent wallet balances
    python scripts/qatom_setup.py tools        # tools the Qatom MCP server offers
    python scripts/qatom_setup.py catalog [q]  # search the catalog (via the MCP catalog_search tool)
    python scripts/qatom_setup.py buy ITEM_ID --yes   # spend real funds on one catalog item

Tokens are written to .qatom/ (git-ignored).
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app.rails.qatom_client import (API, SCOPES, QatomClient, load_oidc_client,  # noqa: E402
                                    save_oidc_client, save_oidc_token)

REDIRECT = "http://localhost:3333/callback"


def cmd_auth() -> None:
    client = load_oidc_client()
    if not client:
        r = httpx.post(f"{API}/v4/oidc/reg", json={
            "client_name": "scamguard", "redirect_uris": [REDIRECT],
            "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
            "token_endpoint_auth_method": "none", "scope": SCOPES})
        if r.status_code >= 400:
            sys.exit(f"Qatom client registration failed ({r.status_code}): {r.text[:300]}")
        client = r.json()
        save_oidc_client(client)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = f"{API}/v4/oidc/auth?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": client["client_id"], "redirect_uri": REDIRECT, "scope": SCOPES,
        "code_challenge": challenge, "code_challenge_method": "S256", "state": state})
    got: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Signed in. You can close this tab.")

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("localhost", 3333), Handler)
    server.timeout = 1
    print("Opening the Qatom sign-in page. If it does not open, visit:\n" + url)
    webbrowser.open(url)
    deadline = time.time() + 300
    while not ("code" in got or "error" in got):     # ignore stray requests such as /favicon.ico
        if time.time() > deadline:
            sys.exit("Sign-in timed out after 5 minutes. Run auth again.")
        server.handle_request()
    server.server_close()
    if got.get("state") != state or "code" not in got:
        sys.exit(f"Sign-in failed: {got}")
    r = httpx.post(f"{API}/v4/oidc/token", data={
        "grant_type": "authorization_code", "code": got["code"], "redirect_uri": REDIRECT,
        "client_id": client["client_id"], "code_verifier": verifier})
    if r.status_code >= 400:
        sys.exit(f"Qatom sign-in failed ({r.status_code}): {r.text[:300]}")
    save_oidc_token(r.json())
    print("Signed in. Token saved to .qatom/oidc_token.json")
    print("Note: as a connected app, every purchase needs approval. It is automatic when the price is at or "
          "under your auto-approve limit in the TODAQ app.")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "auth":
        return cmd_auth()
    c = QatomClient()
    print(f"Auth mode: {c.mode}")
    if cmd == "token":
        tok = c.access_token()
        print("Token OK:", tok[:10] + "…")
    elif cmd == "wallets":
        print(json.dumps(c.wallets(), indent=2))
    elif cmd == "tools":
        for t in c.list_tools():
            print(f"- {t['name']}: {(t.get('description') or '').splitlines()[0][:100]}")
            print("    input:", json.dumps(t.get("inputSchema", {}).get("properties", {}))[:300])
    elif cmd == "catalog":
        res = c.call_tool("catalog_search", {"query": " ".join(args)} if args else {})
        print(json.dumps(res, indent=2)[:6000])
    elif cmd == "buy":
        if not args or "--yes" not in args:
            sys.exit("This spends real funds from the agent wallet. Run: buy ITEM_ID --yes")
        res = c.pay_item(int(args[0]), {})
        print(json.dumps(res, indent=2, default=str)[:4000])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    from app.rails.qatom_client import QatomError
    try:
        main()
    except (QatomError, httpx.HTTPError) as exc:
        sys.exit(f"Qatom: {exc}")
