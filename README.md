# ScamGuard

An AI assistant that pays on a senior's behalf, behind a guard it cannot talk its way past.

The assistant can only **ask**. The **guard** holds the wallet key, checks every request against fixed rules, and either pays, holds the payment for family approval, or blocks it. Even a fully hijacked AI can only lose what the rules allow.

Built for the Agentic Payments Hackathon Toronto (November 2026). Tracks: Use, Control and Attack.

```
Grandma -> AI assistant -> Guard -> approved -> Spending wallet -> Payment rail -> Payee
                                 -> on hold  -> family approves -> same path
                                 -> blocked  -> nothing moves
```

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# open http://localhost:8000
pytest
```

This runs on the practice rail with the built-in parser. No accounts are needed. Press **1 to 6** to run the scenarios, **L** for the ledger, and **Start over** before a demo.

## The rules (`policy.json`)

| Rule | If it fails |
| --- | --- |
| Amount is a real, positive number | Blocked |
| Payment type is allowed (no gift cards, crypto or wires) | Blocked |
| Payee has been paid before | Held for family |
| Amount is within the auto-approve limit ($100) | Held for family |
| Spending wallet covers it ($200 weekly top-up) | Held for family |
| At most 3 payments an hour | Held for family |

- **Hold expiry:** a held payment with no family answer in 24 hours is cancelled.
- **Limits on family:** family approval cannot release a blocked type, or more than the wallet holds. The family has to top up from savings first.
- **Rail failure:** if the rail fails, nothing moves.
- **Claims are never read:** the guard never reads `request.claims`. Those are things the assistant asserts, such as "trusted" or "skip the checks". They are recorded in the ledger and shown as ignored.

## Agent to agent: the scam check

When a payment to a new payee is held, the assistant buys a risk report from a second agent, ScamCheck, for $0.01.

- **Paid like any payment:** the purchase goes through the guard like any other payment. `scam-check` is a known payee and is exempt from the hourly count.
- **Where the report shows:** it is attached to the hold and shown on the daughter's approval card and in the guard panel.
- **It informs, never decides:** the report is never an input to the rules, so it cannot change the verdict. `tests/test_assistant.py` includes a hacked checker that says "release the money", and the hold stays put.

On the practice rail, the checker returns a canned report per payee (`app/scamcheck.py`). On Qatom it is a paid catalog item, and the report is the response body of the purchase.

## Scenarios

| Key | Scenario | What happens |
| --- | --- | --- |
| 1 | Hydro bill | Known payee under $100, so it is paid. The balance drops. |
| 2 | Grandson scam | New payee, over the limit, over the wallet: held. The scam check flags it high risk. The daughter denies it. |
| 3 | Scammer pressures the AI | A message straight to the assistant ("trusted, skip the checks") is held. The claims show as ignored. |
| 4 | Gift card demand | Blocked outright. There is nothing for family to release. |
| 5 | New cleaner | The scam check says low risk, and the payment is held anyway. The daughter approves it and trusts the payee. |
| 6 | Runaway agent | The assistant loops. Payment 4 within an hour is held. |

**Skip 24h** shows hold expiry.

## The 5-minute demo

| Time | What happens | On screen |
| --- | --- | --- |
| 0:00 | The problem. AI assistants are starting to pay for people, and scammers who already talk seniors into paying can now talk the AI into it. | Idle screen |
| 0:25 | How it works. The assistant can only ask, the guard holds the key and decides, and family approves anything unusual. | The three boxes at the top of the guard panel |
| 0:55 | Hydro bill goes straight through, and the balance drops. | 1 |
| 1:25 | Grandson scam is held. The daughter denies it on her phone. | 2, then Deny |
| 2:25 | The scammer pressures the AI and the claims are ignored. Gift cards are blocked, and family cannot release them either. | 3, then 4 |
| 3:05 | Agent to agent. The assistant buys a 1-cent scam check from another agent, through the guard. Low risk, still held: the report informs but cannot decide. | 5, then Approve and trust |
| 3:45 | The money flow. Open the ledger: savings to the spending wallet to the rail to the payee, the receipt, and the hash chain. | L |
| 4:25 | Close: "Even a fully hijacked AI can only lose what the rules allow." | |

That leaves 15 seconds of slack, then 2 minutes of questions. If it runs long, cut the gift card half of the attack, then the how-it-works beat.

Before going on stage:
- Press **Start over**. The rate limit counts every payment in the last hour.
- Have a backup screen recording ready.

## API

| Method and path | What it does | Who |
| --- | --- | --- |
| `GET /api/state` | Everything the screen needs: wallet, holds, decisions, ledger, chat | Anyone |
| `POST /api/chat` `{message}` | Grandma says something, and the assistant asks the guard | Grandma |
| `POST /api/scenario/{id}` | Run a scenario: `hydro`, `grandson`, `pressure`, `giftcard`, `newpayee`, `runaway` | Demo |
| `POST /api/holds/{id}/approve` `{trust_payee}` | Release a held payment | Family, `X-Family-Key` header |
| `POST /api/holds/{id}/deny` | Cancel a held payment | Family, `X-Family-Key` header |
| `POST /api/topup` `{amount}` | Move savings into the spending wallet | Family, `X-Family-Key` header |
| `POST /api/clock/skip` `{hours}` | Skip time forward | Demo mode only |
| `POST /api/reset` | Start over | Demo mode only |
| `GET /api/rail/status` | Live status from the rail | Anyone |
| `GET /api/demo-config` | Hands the family key to the demo page | Demo mode only |

State is in memory and resets when the server restarts. The family key is random on each start unless `FAMILY_KEY` is set.

## Switching to Qatom

How the demo maps onto Qatom:

| Demo | Qatom |
| --- | --- |
| Spending wallet | The agent wallet. The user's own token pays from it with no second factor. |
| Savings | The primary wallet, which needs 2FA |
| Weekly top-up | `transfer_to_agent`, which the user always approves |
| Payee | A catalog item. Paying means buying it: `POST /v4/paywall {catalog_item_id}`. |
| Receipt | The `X-Transaction-Id`, `X-Amount-Charged` and `X-Currency` response headers |

Steps:
1. Copy `.env.example` to `.env`.
2. Add the user's `QATOM_CLIENT_ID` and `QATOM_CLIENT_SECRET`. This is the key the guard holds.
3. Run `python scripts/qatom_setup.py token`, then `wallets`. Fund the agent wallet.
4. Find or create catalog items with `python scripts/qatom_setup.py catalog`. Put each item's id in `payees.json` as `"qatom_item": 123`. Start with `scam-check`: a 1-cent item is the cheapest real payment.
   - **The ScamCheck agent's endpoint:** the server serves it at `POST /api/agents/scamcheck`. It takes `{payee_id, payee_name, context}` and returns `{risk, summary, signals}`.
   - **Pointing the item at it:** set the item's `external_endpoint` to that URL on a public https address, such as a deploy or a tunnel. Set `SCAMCHECK_SECRET` in `.env` and add it to the item's dispatch params as the `X-ScamCheck-Key` header, so only Qatom can call it.
   - **No public address:** create the item with no endpoint. The 1-cent payment is still real, and the report falls back to the canned one.
5. Test one purchase: `python scripts/qatom_setup.py buy ITEM_ID --yes`.
6. Set `RAIL=qatom` and restart.

Things to know:
- **Prices:** catalog prices are fixed per item, so the guard tracks the demo dollar amount, and Qatom settles the item's own price and is the proof that money moved.
- **Payees without an item:** they settle on the practice rail, and the receipt says so. Set `QATOM_UNMAPPED=fail` to refuse them instead.
- **Connected-app sign-in:** without client credentials, `python scripts/qatom_setup.py auth` signs in as a connected app. Every purchase then needs an approval, which is automatic at or under the auto-approve limit set in the TODAQ app.
- **A 502 with `charged: true`:** the client never retries it, because that would pay twice.

Written from the public OpenAPI spec (`https://pay.m.todaq.net/v4/openapi.json`) and the [reference client](https://github.com/TODAQmicro/qatom-skill). It has not run against a live account yet.

## Backboard (LLM)

Set `BACKBOARD_API_KEY` in `.env`, then run `python scripts/backboard_check.py` to see what the model returns for sample messages. The assistant sends each message to `POST https://app.backboard.io/api/threads/messages` with `json_output: true` to extract `{payee, amount, type}`.

Any error or bad output falls back to the built-in parser, and the top bar shows which one is running. Two cross-checks keep the model honest:
- An amount written in the message beats the model's reading of it.
- A gift card, crypto or wire spotted by the parser is never downgraded by the model.

## Layout

| Path | What it is |
| --- | --- |
| `app/guard.py` | Rules, holds, family approval, expiry, top-up |
| `app/ledger.py` | Hash-chained record of every decision |
| `app/assistant.py` | Chat to payment request (Backboard, with the parser as fallback). Explains decisions. |
| `app/scamcheck.py` | The second agent that sells risk reports |
| `app/rails/` | `mock.py` (practice), `qatom.py`, `qatom_client.py` |
| `app/scenarios.py` | Scripted demo scenarios |
| `app/main.py` | FastAPI app |
| `static/index.html` | The one-screen demo |
| `policy.json`, `payees.json` | Rules and the payee directory |
| `tests/` | 17 guard tests (one per rule and attack), plus assistant, API and Qatom-rail tests (31 in all) |
| `SECURITY.md` | Threat model and failure-mode analysis |
| `PAYMENT_FLOW.md` | Who pays whom, every value movement, and a worked example |
| `scripts/backboard_check.py` | Tests the Backboard LLM path with sample messages |
