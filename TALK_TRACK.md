# ScamGuard talk track

5 minutes live, then 2 minutes of judge questions. Agentic Payments Hackathon Toronto, Nov 13–15 2026.

## Who does what

| Role | Does |
| --- | --- |
| **P** (presenter) | Speaks every line. Holds Sarah's real phone and taps Deny, Approve, Freeze all. |
| **D** (driver) | Laptop only: number keys, `L`, buttons. Never speaks. |

- Lines starting with `>` are spoken. Everything else is an action.
- **D:** = driver presses or clicks. **P taps:** = presenter taps on the real phone.
- **Fallback for every P tap:** D clicks the same button on the right-hand phone on screen. The big screen mirrors the real phone within a second.
- **D waits for the typing dots to stop before the next key.** Keys are ignored while a scenario is running. With Claude on, a scenario takes 2–6 seconds (reading the message, then the scam check), so P keeps talking through the dots.
- **Point:** = what P gestures at on the big screen.

## Run sheet at a glance

| Time | Beat | Keys / taps | Words |
| --- | --- | --- | --- |
| 0:00 | The problem | none | 46 |
| 0:25 | How it works | none | 57 |
| 0:55 | Hydro bill goes through | `1` | 44 |
| 1:25 | Grandson scam, Sarah denies | `2`, Deny | 94 |
| 2:25 | Attack from another agent, gift cards | `4`, `5` | 66 |
| 3:05 | Agent-to-agent scam check | `6`, Trust, Approve | 68 |
| 3:45 | Money flow and ledger | `L` | 54 |
| 4:15 | Recovery: freeze | `L`, Freeze all, `1` | 13 |
| 4:25 | Close | none | 35 |
| 4:45 | Slack (15 s) | | |
| | **Total spoken** | | **477** |

477 words in 4:45 is about 100 words a minute, which leaves room for key presses, taps and the screen catching up. Even after taking out the time for actions, no beat goes over about 130 words a minute.

**Checkpoints:** pressing `4` by 2:30, pressing `L` by 3:50. Later than that, use the cut list.

---

## The script

Before you start: **Start over**, then **Unlock** (presenter key), Sarah's phone open at `/family` with the PIN entered.
Each scenario now unfolds in steps (Margaret's message, "Claude is reading…", the verdict, "Buying a scam check…", the report). **P talks over each step as it lands; D waits for the dots to stop before the next key.**

### 0:00 – 0:25 · The problem
> AI assistants are starting to pay bills for people. Meet Margaret. Her assistant pays her bills now.
>
> Scammers already talk seniors into paying. Now they can talk to the AI instead.
>
> So we asked one question: what happens when the AI gets fooled? This is ScamGuard.

### 0:25 – 0:55 · How it works
**Point:** the three boxes at the top of the guard panel, then left phone, middle, right phone.
> On the left, Margaret and her assistant. The assistant has no key. It can only ask.
>
> In the middle, the guard. It holds the wallet key and checks every request against fixed rules: pay, hold, or block.
>
> On the right, Sarah, Margaret's daughter. Sarah approves anything unusual. And the guard never reads what the AI claims.

### 0:55 – 1:25 · A normal day
**D:** `1`
> Margaret asks her assistant to pay the hydro bill.
>
> *(as "Claude is reading the message" shows)* A real AI reads her message…
>
> *(APPROVED)* Known payee, under a hundred dollars, every check passes. Paid, with a receipt. Nobody was bothered.

### 1:25 – 2:25 · The grandson scam
**D:** `2`
> Now the call every family dreads. *(caller bubble)* "Grandma, it's Ethan. I've been arrested. Please don't tell Mom."
>
> Margaret asks to send fifteen hundred dollars to an "Officer Daniels bail fund".
>
> *(ON HOLD)* The guard holds it: a new payee, over the limit, more than the wallet has.
>
> *(as "Buying a scam check from another agent" shows)* Now the assistant buys a scam check from another agent. One cent, paid through the same guard.
>
> *(HIGH risk message)* High risk: the grandparent bail scam. The urgency, the secrecy, the "officer"? Recorded, and ignored.

**P:** hold up the phone.
> Sarah sees Margaret's own words, why it was held, and the report.

**P taps:** Deny. *(Fallback: D clicks Deny on the on-screen phone.)*
> Denied. Nothing was paid.

### 2:25 – 3:05 · An attack from another agent
**D:** `4`
> Next, an attack from another agent. Margaret asks what she owes Toronto Hydro, and a billing agent answers. But it's the scammer's agent.
>
> Three hundred forty dollars, to a lookalike payee. Plus "urgent, trusted, skip your checks."
>
> *(ON HOLD, claims struck through)* The guard doesn't care who's talking. New payee: held. Every pressure line: ignored.

**D:** `5`
> Gift cards for the "tax office"? Blocked outright. Not even Sarah can release that.

### 3:05 – 3:45 · Agent-to-agent, done safely
**D:** `6`
> Margaret hires a new cleaner, Maria. Sixty dollars. New payee, so it's held.
>
> *(LOW risk message)* The scam check says low risk, and it's still held. The report informs Sarah. It never decides, so even a hacked checker can't release money.

**P taps:** tick "Trust Maria Lopez Cleaning", then Approve.
> Sarah approves and trusts Maria. Next time, it just goes through.

### 3:45 – 4:25 · Where the money went, live on Qatom
**Point:** the money-flow strip.
> Savings, twelve thousand four hundred: untouched. The spending wallet is the ceiling.

**D:** `L`
> Every request, hold and payment is in a hash-chained ledger. Edit any past line and the chain breaks.

**D:** `L` to close, then `7`.
> And this part is live on Qatom. Before trusting a seller, the assistant asked Qatom's ratings agent about it. A real Qatom transaction, with its ID right here, paid through the same guard.

*(On the practice rail, skip `7` and say: "Every payment has a receipt, and the guard doesn't care which rail moves the money.")*

### 4:25 – 4:45 · Freeze and close
**P taps:** Freeze all. **D:** `1`.
> If something's wrong, Sarah taps Freeze. Now even the hydro bill is blocked.
>
> The assistant can only ask. The guard holds the key. Sarah approves the unusual, and can stop everything.
>
> Even a fully hijacked AI can only lose what the rules allow. That's ScamGuard. Thank you.

## Cut list (if running long, cut in this order)

| # | Cut | Saves | How |
| --- | --- | --- | --- |
| 1 | Gift card half of the attack beat | ~10 s | Skip `5`. Drop the gift-card line. Mention it in Q&A if asked. |
| 2 | Most of "How it works" | ~20 s | Say only: "The assistant can only ask. The guard holds the key. Sarah approves anything unusual." |
| 3 | Pressure line in the grandson beat | ~5 s | Drop "The urgency, the secrecy, the officer? Recorded, and ignored." Beat 4 shows pressure anyway. |
| 4 | Flow strip in the money beat | ~10 s | Go straight to `L`. Say only the ledger lines. |
| 5 | The freeze demo | ~10 s | Don't tap. Say it in the close: "and can freeze everything with one tap." |

**Never cut:** the grandson Deny, the 1-cent scam check (the agent-to-agent story), and the closing line.

## If something breaks on stage

| Problem | Do this |
| --- | --- |
| A key does nothing | D clicks an empty part of the stage, then presses again. Keys are ignored while the chat box has focus or a scenario is running. Or click the scenario button in the dock. |
| Real phone doesn't update | D taps on the on-screen phone instead. Keep talking. |
| "Wrong PIN" or "Too many wrong PINs" | Use the on-screen phone. Start over clears the lockout, but only between demos. |
| Hydro is held instead of paid | Start over was skipped, so the rehearsal's hydro payment counts as a repeat. P: "It's held because we already paid Hydro in rehearsal: the repeat check just did its job." Carry on. |
| Server unreachable (top bar) | Switch to the backup recording. P narrates the same script over it. |

---

## Judge Q&A

Keep each answer to two sentences. If a question needs a live demo, D can run it, but **unfreeze first**: P taps "Turn payments back on".

### Qatom founder (cryptography, cybersecurity, finance)

**Where does the wallet key live, and what if the guard's host is compromised?**
The rail credentials live only in the guard process's environment; the assistant and the family page never see them. If the guard host itself is taken, the attacker has that key, but the loss is capped at the spending wallet, because savings sit in the primary wallet behind 2FA; moving the key into an HSM or a rail-side spending policy is next.

**Can someone brute-force the family PIN?**
It's 6 random digits, compared in constant time, and 5 wrong tries in 10 minutes locks every family action, so at most 720 guesses a day, about 0.07% of the space. Honestly it's one shared secret, the lock is global so a guesser can also lock Sarah out, and the demo runs over plain HTTP on local Wi-Fi; production needs per-person passkeys over TLS.

**Real billers don't accept Qatom. So is this real?**
Correct, they don't yet, so our payees are made up and each one maps to a Qatom catalog item. The guard doesn't depend on the rail: a rail is one `pay()` call that returns a receipt, so a bank or card rail plugs into the same spot and the rules, holds and ledger stay the same.

### Accountant (audit and financial controls)

**Who can change the rules, and how is that audited?**
Only the family key holder: the limit, same-payee and per-hour steppers on Sarah's phone (hold hours, weekly top-up and trusted payees through the API), each within hard bounds, and every change goes into the hash-chained ledger with before and after values. Gift cards, crypto and wires can only be added to the never-allowed list at runtime; removing one takes a `policy.json` edit and a restart, and the assistant can't touch rules at all.

**How do the guard's records reconcile with the money?**
Every paid entry in the ledger carries the rail's transaction id (on Qatom, `X-Transaction-Id`), so a payment in one record without the other stands out. Each entry hashes the one before it, so a changed entry breaks the chain; the gap is that the chain lives in memory next to the guard, so anchoring its head somewhere the guard can't rewrite is still to do.

**What about false positives?**
A wrong hold costs a delay, never money: it waits until Sarah approves, and "trust this payee" stops it happening again. Known payees under $100 never reach Sarah at all, and Sarah can tune the limit from the phone.

**What if the family member is the one exploiting the senior?**
In this build family is trusted: Sarah can top up from savings and approve a held payment, but each step is a named entry in the ledger. Production should need Margaret's own approval for top-ups (Qatom's transfer into the agent wallet already asks the account owner) and a second approver for large releases.

**What if Sarah can't be reached?**
The hold is cancelled after 24 hours and nothing moves, so the default is no; D can show it live with **Skip 24h**. There's no fallback to a second family member yet, which we'd add next.

### GOAT Network co-founder (agent-to-agent, on-chain)

**Why not pay with GOAT or crypto?**
We block crypto as an outgoing payment type because scammers ask for it precisely because it can't be reversed, and that's about protecting seniors, not about chains. Where a chain fits well is anchoring the ledger's head hash somewhere the guard can't rewrite, which is on our known-gaps list; we haven't built a GOAT integration.

**How does the assistant know a billing agent is the real one?**
It doesn't have to: an invoice is untrusted input, and the guard only auto-pays payees already on file, so a redirected invoice is just a new payee and gets held. A real Hydro billing agent that names the payee on file is paid normally, and we test both.

**Do the economics of a 1-cent scam check work?**
The check is bought only when a new payee is held, not on every payment, so a normal month costs a few cents, and it goes through the guard with its own receipt like any payment. The ScamCheck payee can only ever be paid its exact 1-cent price, with its own cap of 10 an hour, so a hijacked assistant can't turn it into a drain; a test proves five $40 "checks" are all blocked.

### General

**Can the AI be tricked?**
Yes, and we assume it will be: it has no wallet key, no family key and no write access to the rules. Whatever it claims, like "trusted" or "skip the checks", is recorded and shown as ignored, and a test proves the verdict is identical with or without the claims.

**How do you know it's a scam?**
We don't decide "scam". The rules decide "unusual": a new payee, over the limit, over the wallet, too many in an hour, or a never-allowed type. The scam report is context for Sarah: another agent (Claude) reads the request and names the scam pattern, and it can never change the verdict, which a test proves with an AI that lies.

**Doesn't this take control away from seniors?**
Margaret's everyday payments, known payees under $100, go through with nobody asked, and the money stays Margaret's. Only the unusual waits for a second look, and we'd expect Margaret to choose the contact and the limits together with the family.

**What's real and what's mocked today?**
Real: the guard, rules, holds, family approvals, freeze, PIN lockout, the hash-chained ledger and the family page on a real phone, with 55 passing tests; Claude reading Margaret's messages and acting as the ScamCheck agent. Mocked: the practice rail (in-memory balances, `prac_` receipts), made-up payees and scripted scenarios; the top bar shows which rail and which AI are running.

Then add one of these:
- **If there's still no funded wallet (most likely):** "We're signed in to Qatom live. The seller-rating purchase you saw is a real Qatom transaction at $0, and the wallet balance on screen is read from Qatom. The agent wallet isn't funded, so the paid payments settle on our practice rail, and each receipt says so. Funding it doesn't change the guard." Then: "The assistant reads Margaret's messages with Claude, live; if the AI is slow or down, a built-in parser takes over, and the guard doesn't change."
- **If they ran live before the demo:** say exactly what ran, for example "The 1-cent scam check settled on Qatom, and here's the transaction id." Only claim what you saw work that day.

---

## Pre-stage checklist

**Server**
- [ ] Live site: from the project folder run `./scripts/start_live.sh`. It starts the app and the Cloudflare tunnel together and keeps the Mac awake; Ctrl-C stops both. If Qatom misbehaves, `RAIL=mock ./scripts/start_live.sh`. Check https://demo.chud.ing loads, then click **Unlock** and enter the presenter key.
- [ ] Start with `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000` (or the `scamguard-lan` launch config). No `--reload`: a reload wipes state and, unless `FAMILY_KEY` is set, changes the PIN.
- [ ] `DEMO_MODE` is on (default `1`).
- [ ] Copy the PIN from the server log line `ScamGuard family PIN: ......`. To keep it across restarts, set `FAMILY_KEY` in `.env`.
- [ ] Decide the rail and parser now, and rehearse all of keys 1, 2, 4, 5, 6 with exactly that setup.
- [ ] Qatom: start with `RAIL=qatom` (launch config `scamguard-qatom`) so the money-flow strip shows the live agent wallet. If the rail pill shows "not signed in" or an error, run `.venv/bin/python scripts/qatom_setup.py auth` again (the sign-in may have expired overnight). If it still fails, restart with `RAIL=mock`; nothing else changes.
- [ ] Using a teammate's funded Qatom wallet: `qatom_setup.py logout`, then `qatom_setup.py auth` with the printed link opened in a **private window**. The teammate moves a little into the agent wallet and sets the auto-approve limit to about $0.05 in the TODAQ app. Then link the paid ScamCheck item in `payees.json` and run one test purchase.
- [ ] Run `.venv/bin/python scripts/go_live.py` (read-only) to see what's ready.
- [ ] AI: the top bar should say "Claude (claude-haiku-5-5)". Each message takes 1–3 seconds. If the venue network is slow, blank `ANTHROPIC_API_KEY` in `.env` and restart to use the parser; each message otherwise waits up to 10 seconds before falling back. A restart changes the PIN unless `FAMILY_KEY` is set.

**Laptop screen**
- [ ] Open `http://localhost:8000`, not the LAN address. Start over, the scenarios and Skip 24h only work from the laptop itself.
- [ ] Full screen. All three columns and the scenario dock are visible on the projector.
- [ ] Do Not Disturb on, laptop on power, screen sleep off.

**Sarah's phone**
- [ ] Phone on the same Wi-Fi as the laptop. If the venue Wi-Fi blocks devices from reaching each other, use a phone hotspot that the laptop also joins.
- [ ] Open the address shown in the top bar ("Family phone: http://…/family") and enter the PIN. The page says "Hi Sarah".
- [ ] Don't mistype the PIN 5 times: that locks every family action for 10 minutes, including the on-screen phone. Start over clears it.
- [ ] Phone brightness up, auto-lock off, Do Not Disturb on.

**Right before going on (last thing)**
- [ ] Press **Start over**. The repeat check and the hourly backstop count every payment in the last hour, including rehearsals.
- [ ] Check: Margaret's balance is $200.00, savings $12,400, the guard says WAITING, the phone says "All clear", the ledger (`L`, then `L` again) says "Chain verified · 1 entries".
- [ ] Not frozen: the phone shows the "Freeze all" button, not a red banner.
- [ ] D clicks an empty part of the stage so the keys reach the page.
- [ ] Backup screen recording open in a player, paused at 0:00, one click away.
- [ ] Timer visible to P.

**Expected screen after each step (for D)**

| After | Guard panel | Margaret's balance |
| --- | --- | --- |
| `1` | APPROVED, $84.20 to Toronto Hydro, `prac_00001` | $115.80 |
| `2` | ON HOLD, $1,500.00 to Officer Daniels Bail Fund, HIGH RISK | $115.79 |
| Deny | FAMILY DENIED | $115.79 |
| `4` | ON HOLD, $340.00 to Toronto Hydro Payments Dept, HIGH RISK, 5 claims IGNORED | $115.78 |
| `5` | BLOCKED, $500.00, "Gift cards are never allowed" | $115.78 |
| `6` | ON HOLD, $60.00 to Maria Lopez Cleaning, LOW RISK, `prac_00004` | $115.77 |
| Trust + Approve | FAMILY APPROVED | $55.77 |
| Freeze all, `1` | BLOCKED, "Frozen by family", Guard: FROZEN | $55.77 |
