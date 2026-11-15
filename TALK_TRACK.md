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
- **D waits for the typing dots to stop before the next key.** Keys are ignored while a scenario is running.
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

### 0:00 – 0:25 · The problem (46 words, 25 s)

Screen: idle after Start over. Margaret's balance shows $200.00. The guard panel says WAITING.

> AI assistants are starting to pay for people. Meet Margaret. An assistant pays Margaret's bills now.
>
> Scammers already talk seniors into paying. Now they can talk to the AI instead.
>
> So we built for one question: what happens when the AI gets fooled? This is ScamGuard.

### 0:25 – 0:55 · How it works (57 words, 30 s)

**Point:** the three boxes at the top of the guard panel: AI assistant, Guard, Family. Then the left phone, the middle panel, the right phone.

> On the left, Margaret's phone and the assistant. The assistant has no key. It can only ask.
>
> In the middle, the guard. It holds the wallet key and checks every request against fixed rules: pay, hold, or block.
>
> On the right, Sarah, Margaret's daughter. Sarah approves anything unusual.
>
> And the guard never reads what the AI claims.

### 0:55 – 1:25 · Hydro bill goes through (44 words, 30 s)

> First, a normal day. Margaret asks the assistant to pay the Toronto Hydro bill.

**D:** press `1`.

**Point:** green APPROVED stamp, the row of green PASS checks, the receipt `prac_00001`. Margaret's balance drops from $200.00 to $115.80.

> Known payee. Eighty-four dollars, under the hundred-dollar limit. Every check passes.
>
> Paid, with a receipt. Margaret's spending money drops. Savings are never touched.
>
> Nobody was bothered. Everyday bills just work.

### 1:25 – 2:25 · Grandson scam, Sarah denies (94 words, 60 s)

> Now the call every family dreads.

**D:** press `2`.

**Point:** the grey caller bubble on Margaret's phone.

> "Grandma, it's Ethan. I've been arrested. Please don't tell Mom."
>
> Margaret believes it, and asks the assistant to send fifteen hundred dollars to an Officer Daniels bail fund.

**Point:** ON HOLD stamp, the three amber HOLD rows.

> The guard holds it, for three reasons: a new payee, over the limit, and more than the wallet has.

**Point:** red HIGH RISK report, then the struck-through claims marked IGNORED.

> The assistant also bought a scam check from another agent. High risk: it matches the grandparent bail scam.
>
> The urgency, the secrecy, the "officer"? Recorded, and ignored.

**P:** hold up the phone so the card is visible.

> Sarah sees Margaret's own words, the reasons, and the report.

**P taps:** Deny. (Fallback: D clicks Deny on the on-screen phone.)

**Point:** FAMILY DENIED stamp. Margaret's chat says nothing was paid and to call Sarah.

> Denied. Nothing was paid.

### 2:25 – 3:05 · Attack from another agent, then gift cards (66 words, 40 s)

> Next, an attack from another agent.

**D:** press `4`.

**Point:** the invoice bubble from "Toronto Hydro Billing (unverified agent)", then the payee name in the guard panel: "Toronto Hydro Payments Dept", not "Toronto Hydro".

> Margaret asks what's owed to Toronto Hydro. A billing agent answers. But it's the scammer's agent.
>
> Three hundred forty dollars, to a lookalike payee. Plus "urgent, trusted, skip your checks."

**Point:** ON HOLD, and the five struck-through pressure lines marked IGNORED.

> The guard doesn't care who's talking. New payee: held. Every pressure line: ignored.

**D:** press `5`.

**Point:** red BLOCKED stamp, "Gift cards are never allowed".

> Gift cards for the "tax office"? Blocked outright. There's no hold, so Sarah can't release it either.

### 3:05 – 3:45 · Agent-to-agent: the 1-cent scam check (68 words, 40 s)

> Now agent-to-agent commerce, done safely.

**D:** press `6`.

**Point:** ON HOLD with one reason, "never been paid before". Then the green report box: "ScamCheck Agent · $0.01 · prac_00004 · LOW RISK" and the line "It cannot change the verdict."

> Margaret wants to pay a new cleaner, Maria, sixty dollars. New payee, so it's held.
>
> The assistant buys a scam check from another agent. One cent, paid through the same guard.
>
> Low risk. Still held. The report informs Sarah. It never decides, so even a hacked checker can't release money.

**P taps:** tick "Trust Maria Lopez Cleaning from now on", then Approve. Tick first, or the trust is lost. (Fallback: D does both on the on-screen phone.)

**Point:** FAMILY APPROVED stamp. Margaret's balance is $55.77.

> Sarah approves and trusts Maria. Paid. Next time, Maria is a known payee.

### 3:45 – 4:15 · Where the money went (54 words, 30 s)

**Point:** the flow strip at the bottom of the guard panel: Savings $12,400, then Spending wallet $55.77, then Payment rail, then Payee.

> Savings: twelve thousand four hundred, untouched.
>
> The spending wallet is the ceiling. The guard pays through the rail, and every payment has a receipt.

**D:** press `L`.

**Point:** "Chain verified" at the top of the ledger, then the Hash column.

> Every request, hold, denial and payment is in a hash-chained ledger. Edit any past entry and the chain breaks.
>
> Scammers asked for twenty-three hundred forty dollars. None of it left.

*Only if the Qatom rail is live and the ScamCheck item is mapped:* swap "The guard pays through the rail, and every payment has a receipt" for "That one-cent scam check settled on Qatom for real. There's its transaction id." Check before the demo that the ledger shows `via qatom` for the scam-check row. Otherwise keep the default line.

### 4:15 – 4:25 · Recovery: freeze (13 words, 10 s)

**D:** press `L` to close the ledger.

> Something wrong?

**P taps:** Freeze all. (Fallback: D clicks Freeze all on the on-screen phone.)

**D:** press `1`.

**Point:** red BLOCKED stamp, "Frozen by family". The guard box turns red: "Guard: FROZEN".

> Sarah taps Freeze all. Now even the hydro bill is blocked.

### 4:25 – 4:45 · Close (35 words, 20 s)

**Point:** the line under the logo: "The AI can only ask. The guard holds the key."

> So: the assistant can only ask. The guard holds the key. Sarah approves the unusual, and can stop everything.
>
> Even a fully hijacked AI can only lose what the rules allow.
>
> That's ScamGuard. Thank you.

---

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
| Hydro is held instead of paid | Start over was skipped and the hourly limit counted rehearsal payments. P: "It's held because of the rehearsal: the hourly limit just did its job." Carry on. |
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
Only the family key holder: the limit and payments-per-hour steppers on Sarah's phone (hold hours, weekly top-up and trusted payees through the API), each within hard bounds, and every change goes into the hash-chained ledger with before and after values. Gift cards, crypto and wires can only be added to the never-allowed list at runtime; removing one takes a `policy.json` edit and a restart, and the assistant can't touch rules at all.

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
We don't decide "scam". The rules decide "unusual": a new payee, over the limit, over the wallet, too many in an hour, or a never-allowed type. The scam report is context for Sarah, it's canned per payee on the practice rail, and it can never change the verdict.

**Doesn't this take control away from seniors?**
Margaret's everyday payments, known payees under $100, go through with nobody asked, and the money stays Margaret's. Only the unusual waits for a second look, and we'd expect Margaret to choose the contact and the limits together with the family.

**What's real and what's mocked today?**
Real: the guard, rules, holds, family approvals, freeze, PIN lockout, the hash-chained ledger and the family page on a real phone, with 44 passing tests. Mocked: the practice rail (in-memory balances, `prac_` receipts), canned scam reports, made-up payees and scripted scenarios; the top bar shows which rail and which parser are running.

Then add one of these:
- **If Qatom and Backboard still haven't run live:** "The Qatom rail and the Backboard client are written from their public specs and tested against fakes, but haven't run against live accounts yet. When they do, the guard doesn't change."
- **If they ran live before the demo:** say exactly what ran, for example "The 1-cent scam check settled on Qatom, and here's the transaction id." Only claim what you saw work that day.

---

## Pre-stage checklist

**Server**
- [ ] Start with `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000` (or the `scamguard-lan` launch config). No `--reload`: a reload wipes state and, unless `FAMILY_KEY` is set, changes the PIN.
- [ ] `DEMO_MODE` is on (default `1`).
- [ ] Copy the PIN from the server log line `ScamGuard family PIN: ......`. To keep it across restarts, set `FAMILY_KEY` in `.env`.
- [ ] Decide the rail and parser now, and rehearse all of keys 1, 2, 4, 5, 6 with exactly that setup.
- [ ] Going live on Qatom: run `.venv/bin/python scripts/go_live.py` (read-only). Exit 0 means ready. If the rail pill shows a warning on stage day, restart with `RAIL=mock`.
- [ ] Backboard: if the venue network is slow, unset `BACKBOARD_API_KEY` and restart. Each message can wait up to 10 seconds (`BACKBOARD_TIMEOUT`) before falling back to the parser. A restart changes the PIN unless `FAMILY_KEY` is set.

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
- [ ] Press **Start over**. The hourly limit counts every payment in the last hour, including rehearsals.
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
