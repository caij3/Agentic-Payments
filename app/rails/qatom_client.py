"""Small Qatom (TODAQ) client. Written from the public OpenAPI spec at
https://pay.m.todaq.net/v4/openapi.json and the reference client in
https://github.com/TODAQmicro/qatom-skill. Not yet run against a live account.

Two ways to authenticate:

1. User client credentials (QATOM_CLIENT_ID / QATOM_CLIENT_SECRET), exchanged at
   POST /v4/user/oauth/token. Per the spec, the user's own bearer token pays from the
   agent wallet immediately, with no second factor. This is the key the guard holds.

2. OIDC sign-in as a connected app (PKCE, like the MCP server uses). Every purchase
   then needs an approval (POST /v4/agent/approvals). It is approved at once when
   the price is at or under the user's auto-approve limit; otherwise the user
   is asked in the TODAQ app.

Paying = buying a catalog item: POST /v4/paywall {catalog_item_id, ...arguments}.
The receipt is in the response headers: X-Transaction-Id, X-Amount-Charged, X-Currency.
"""
from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

API = os.getenv("QATOM_API", "https://pay.m.todaq.net")
MCP_URL = os.getenv("QATOM_MCP_URL", "https://mcp.m.todaq.net/mcp")
# Absolute, so the sign-in is found whichever folder the server or a script starts from.
TOKEN_DIR = Path(os.getenv("QATOM_TOKEN_DIR") or Path(__file__).resolve().parents[2] / ".qatom")
SCOPES = "openid profile email twin offline_access"


class QatomError(Exception):
    def __init__(self, message: str, status: int | None = None, body: Any = None, headers: dict | None = None):
        super().__init__(message)
        self.status = status
        self.body = body
        self.headers = headers or {}


def _save(name: str, data: dict) -> None:
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    path = TOKEN_DIR / name
    path.write_text(json.dumps(data, indent=2))
    os.chmod(path, 0o600)


def _load(name: str) -> dict | None:
    path = TOKEN_DIR / name
    try:
        return json.loads(path.read_text()) if path.exists() else None
    except (OSError, ValueError):
        return None          # a corrupt token file counts as signed out, never a crash


class QatomClient:
    def __init__(self, client_id: str | None = None, client_secret: str | None = None, timeout: float = 20.0):
        self.client_id = client_id if client_id is not None else os.getenv("QATOM_CLIENT_ID", "")
        self.client_secret = client_secret if client_secret is not None else os.getenv("QATOM_CLIENT_SECRET", "")
        self.http = httpx.Client(timeout=timeout)
        self._mcp_session: str | None = None
        self._rpc_id = 0

    # ------------------------------------------------------------------ auth
    @property
    def mode(self) -> str:
        if self.client_id and self.client_secret:
            return "user"
        if _load("oidc_token.json"):
            return "oidc"
        return "none"

    def access_token(self) -> str:
        if self.mode == "user":
            return self._user_token()
        if self.mode == "oidc":
            return self._oidc_token()
        raise QatomError("Not signed in to Qatom. Set QATOM_CLIENT_ID/SECRET or run scripts/qatom_setup.py auth")

    def _user_token(self) -> str:
        cached = _load("user_token.json")
        if cached and cached.get("expires_at", 0) - time.time() > 300:
            return cached["access_token"]
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        r = self.http.post(f"{API}/v4/user/oauth/token", headers={"Authorization": f"Basic {basic}"})
        self._raise(r, "Getting a Qatom token")
        data = r.json()
        if "expires_at" not in data and "expires_in" in data:
            data["expires_at"] = int(time.time()) + int(data["expires_in"])
        _save("user_token.json", data)
        return data["access_token"]

    def _oidc_token(self) -> str:
        tok = _load("oidc_token.json") or {}
        if tok.get("expires_at", 0) - time.time() > 60:
            return tok["access_token"]
        client = _load("oidc_client.json") or {}
        if not tok.get("refresh_token") or not client.get("client_id"):
            raise QatomError("Qatom sign-in expired. Run scripts/qatom_setup.py auth again")
        r = self.http.post(f"{API}/v4/oidc/token", data={
            "grant_type": "refresh_token", "refresh_token": tok["refresh_token"], "client_id": client["client_id"]})
        self._raise(r, "Refreshing the Qatom sign-in")
        save_oidc_token(r.json())          # refresh tokens are single-use: store the new pair now
        return r.json()["access_token"]

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token()}"}

    @staticmethod
    def _raise(r: httpx.Response, what: str) -> None:
        if r.status_code >= 400:
            try:
                body = r.json()
            except ValueError:
                body = r.text[:500]
            raise QatomError(f"{what} failed ({r.status_code}): {body}", r.status_code, body, dict(r.headers))

    # ------------------------------------------------------------------ REST
    def wallets(self) -> dict:
        r = self.http.get(f"{API}/v4/wallets", headers=self._auth())
        self._raise(r, "Reading wallets")
        return r.json()

    def agent_balance(self) -> str:
        data = self.wallets()
        for w in data.get("wallets", []):
            if w.get("role") == "agent":
                bal = w.get("balances") or []
                return ", ".join(f"{b.get('amount')} {b.get('currency', '')}".strip() for b in bal) or "empty"
        return "no agent wallet"

    def request_approval(self, item_id: int, arguments: dict) -> dict:
        r = self.http.post(f"{API}/v4/agent/approvals", headers=self._auth(),
                           json={"kind": "purchase", "catalog_item_id": item_id, "arguments": arguments})
        self._raise(r, "Asking Qatom for purchase approval")
        return r.json()

    def buy(self, item_id: int, arguments: dict | None = None, approval_id: str | None = None) -> dict:
        """Buy one catalog item. Returns {tx_id, charged, currency, body}. Never retried automatically."""
        payload: dict[str, Any] = {"catalog_item_id": int(item_id), **(arguments or {})}
        if approval_id:
            payload["approval_id"] = approval_id
        r = self.http.post(f"{API}/v4/paywall", headers=self._auth(), json=payload)
        if r.status_code == 502:
            # Payment may have settled with only delivery failing. Do NOT retry: that would pay twice.
            try:
                body = r.json()
            except ValueError:
                body = {"text": r.text[:500]}
            if isinstance(body, dict) and body.get("charged"):
                return {"tx_id": r.headers.get("X-Transaction-Id") or body.get("purchase_id"),
                        "charged": r.headers.get("X-Amount-Charged"), "currency": r.headers.get("X-Currency"),
                        "body": body, "delivery_failed": True}
        self._raise(r, "Qatom payment")
        try:
            body: Any = r.json()
        except ValueError:
            body = r.text[:2000]
        return {"tx_id": r.headers.get("X-Transaction-Id"), "charged": r.headers.get("X-Amount-Charged"),
                "currency": r.headers.get("X-Currency"), "body": body}

    def pay_item(self, item_id: int, arguments: dict | None = None) -> dict:
        """Pay, getting an approval first when signed in as a connected app."""
        approval_id = None
        if self.mode == "oidc":
            res = self.request_approval(item_id, arguments or {})
            appr = res.get("approval") or {}
            if res.get("required") is False:
                approval_id = None
            elif appr.get("state") == "approved":
                approval_id = appr.get("id")
            else:
                raise QatomError(f"Qatom wants the user to approve this purchase: {appr.get('approve_url', '')}",
                                 body=res)
        return self.buy(item_id, arguments, approval_id)

    # ------------------------------------------------------------------ MCP (catalog search, tool listing)
    def _rpc(self, method: str, params: dict | None = None, notify: bool = False) -> dict:
        headers = {**self._auth(), "Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self._mcp_session:
            headers["Mcp-Session-Id"] = self._mcp_session
        msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if not notify:
            self._rpc_id += 1
            msg["id"] = self._rpc_id
        r = self.http.post(MCP_URL, headers=headers, json=msg)
        self._mcp_session = r.headers.get("mcp-session-id") or self._mcp_session
        self._raise(r, f"MCP {method}")
        if notify or not r.content:
            return {}
        if "text/event-stream" in r.headers.get("content-type", ""):
            data = "".join(line[6:] for line in r.text.splitlines() if line.startswith("data: "))
            out = json.loads(data) if data else {}
        else:
            out = r.json()
        if "error" in out:
            raise QatomError(f"MCP {method}: {out['error']}", body=out)
        return out.get("result", out)

    def mcp_init(self) -> dict:
        res = self._rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                       "clientInfo": {"name": "scamguard", "version": "0.1.0"}})
        self._rpc("notifications/initialized", notify=True)
        return res

    def list_tools(self) -> list[dict]:
        if not self._mcp_session:
            self.mcp_init()
        return self._rpc("tools/list").get("tools", [])

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        if not self._mcp_session:
            self.mcp_init()
        return self._rpc("tools/call", {"name": name, "arguments": arguments or {}})


def save_oidc_token(data: dict) -> None:
    if "expires_in" in data and "expires_at" not in data:
        data["expires_at"] = int(time.time()) + int(data["expires_in"])
    _save("oidc_token.json", data)


def save_oidc_client(data: dict) -> None:
    _save("oidc_client.json", data)


def load_oidc_client() -> dict | None:
    return _load("oidc_client.json")
