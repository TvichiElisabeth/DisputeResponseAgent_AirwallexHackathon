# Dispute Response Agent

An agent that works through a merchant's chargeback queue on the **Airwallex sandbox**. For each case it decides whether to **challenge**, **accept**, or **hand it to a person**. It moves real (sandbox) money and dispute state, asks a person before anything risky, and changes its mind when the issuing bank pushes back.

Built for the Airwallex agentic banking hackathon, **Kit 4: Dispute Response Agent**.

<!-- ![Demo](docs/demo.gif) -->

---

## The problem

A finance ops lead at an online merchant faces a queue of chargebacks. Each one has a **deadline**, a **disputed amount** and some **order evidence**. Defending a dispute costs a fee **even if you win**, so fighting a small one can cost more than giving it up. Fighting a large one with weak evidence just loses money more slowly.

The decision in each case is: **challenge, accept, or escalate?** The right answer changes when the amount, the evidence, the deadline or the bank's response changes.

## The demo story

| Beat | What happens |
|---|---|
| **Goal** | Clear the queue before the deadlines without spending more on fees than we recover |
| **Queue** | Three disputes, read from Airwallex: amount, Visa reason code, stage, deadline |
| **Initial plan** | The agent proposes: **escalate C** (urgent), **accept B** (automatic), **challenge A** (needs approval), with the reasons and the numbers |
| **Actions** | C goes to a person with a checklist. B is accepted and refunded. A's evidence PDF is uploaded and the challenge is sent after a person approves |
| **New information** | The issuing bank rejects A's evidence: RFI → CHARGEBACK, back to `REQUIRES_RESPONSE` |
| **Revised decision** | Win chance drops from 85% to 34%, and fighting on costs a $500 arbitration fee. The agent switches **CHALLENGE → ACCEPT** and explains why. A person approves |
| **Result** | Final statuses, the refund record, and a money summary: refunded, conceded, fees paid, waiting on a person |

### The three cases

| Case | Claim | Amount | Evidence | Decision |
|---|---|---|---|---|
| **A** | Fraud (Visa 10.4) | $1,240 | Same device fingerprint and IP as 3 earlier undisputed orders; delivery signed for | **Challenge** with evidence (approval needed) |
| **B** | Not received (Visa 13.1) | $18 | Delivery scan, but no signature and no photo | **Accept + refund** automatically: the $25 fee exceeds the amount at risk |
| **C** | Credit not processed (Visa 13.6) | $340 | Customer emailed support twice, no reply; return never logged | **Escalate** to a person, flagged URGENT (2 days left) |

## Who does what

The core design choice: **code decides, the model reads and explains, a person approves.**

| Piece | Job | Where |
|---|---|---|
| **Model (Claude)** | Reads messy evidence (order tables, carrier logs, support emails) and returns **typed facts**. Explains each decision in plain language, including why a decision changed | `merchant/reader.py`, `merchant/explainer.py` |
| **Code** | Every money rule: fee, win chance, expected cost, thresholds, deadlines, state guards, duplicate protection | `merchant/policy.py` |
| **Person** | Approves large or post-rejection actions; decides escalated cases | `merchant/approvals.py` |
| **Agent** | Runs the loop: queue → facts → decision → explanation → plan → approval → action | `merchant/agent.py` |

The model never sees Airwallex credentials, never calls Airwallex, and never chooses an action. It answers only through a **typed tool** (a JSON schema). Code validates every value before the policy uses it. If the model fails to read the evidence, the run stops; if it fails to explain, the agent falls back to the rule's own wording.

## The decision rules (`merchant/policy.py`)

All numbers are demo assumptions, kept in one place:

| Setting | Value | Meaning |
|---|---|---|
| `DISPUTE_FEE` | $25 | Paid whenever we defend, win or lose (the sandbox doesn't deduct it, so the app does) |
| `ARBITRATION_FEE` | $500 | Cost of fighting on after the bank rejects our evidence |
| `AUTO_APPROVE_LIMIT` | $50 | Above this, a person approves |
| `MIN_CHALLENGE_PROB` | 50% | Don't fight weak cases |
| `REJECTION_FACTOR` | 0.4 | After a rejection, the win chance drops to 40% of what it was |
| `MIN_DAYS_TO_CHALLENGE` | 2 days | Less time and no evidence prepared: a person decides |
| `URGENT_DAYS` | 3 days | Needs a person and less time: flagged URGENT |

Rules, checked in order:
1. **Fee ≥ amount → accept.** Even a certain win loses money (case B).
2. **Customer contacted support 2+ times with no reply and no refund → escalate.** The merchant may owe a refund; a person decides (case C).
3. **Otherwise compare expected costs.** Challenge only if the win chance is at least 50% **and** `fee + (1 − p) × amount` is less than the amount. After a rejection, the original fee is sunk and only the $500 arbitration fee counts (case A, before and after).
   - Worth challenging but under 2 days left and no evidence prepared → **escalate as URGENT**, rather than giving up money because of the clock.

The win chance is a simple score per claim type (e.g. fraud: 15% base, +55% for Visa Compelling Evidence 3.0-style device/IP matches, +15% for a signed delivery). A real merchant would replace these weights with its own historical win rates.

## Safety and correctness

- **Approvals are bound to what the person saw.** The approval stores a SHA-256 hash of the action, amount, currency, counterparty, order, product, reason code and evidence file. Right before acting, the agent recomputes it; if anything changed, the approval is void.
- **No double refunds.** A refund is only attached at the RFI stage (at CHARGEBACK the bank has already taken the money back), and `can_refund()` checks the real refund records first.
- **Idempotency.** One `request_id` per operation, reused on retries; every action is logged once per dispute and stage, so reruns never repeat anything.
- **State transitions in code.** Guards refuse to decide on closed or expired disputes, to create disputes at `PRE_CHARGEBACK`, to escalate from `CHARGEBACK`, or to ask for a final ruling on an accepted dispute.
- **Sandbox only.** The app refuses to start unless both API URLs are sandbox URLs.
- **Least privilege.** A scoped API key with only the permissions the agent needs (below). No payout, transfer or FX permissions.
- **Prompt injection.** The model is told the evidence is data, not instructions.
- **One interface for the bank side.** All sandbox simulation calls go through `bank/sandbox.py` (`DisputeSimulator`), so they can be replaced by a real issuer feed or a test fake without touching the decision logic.

## Project structure

```
core/        config.py (sandbox-only settings), client.py (login, token refresh, errors)
bank/        sandbox.py (simulator interface), seed.py (open disputes),
             reject.py (bank rejects evidence), resolve.py (final ruling)
merchant/    record_payments.py, queue.py, reader.py, explainer.py, llm.py,
             policy.py, approvals.py, evidence_files.py, actions.py, refunds.py, agent.py
records/     cases.py, evidence_text.py, state.py, reset.py
tests/       test_policy.py, test_approvals.py
run_demo.py  the whole story in one command
```

## Airwallex endpoints used

| Endpoint | Used for |
|---|---|
| `POST /api/v1/authentication/login` | Bearer token (refreshed automatically) |
| `POST /pa/payment_intents/create` | Creating payments (see sandbox notes) |
| `GET /pa/payment_intents` | Recording the paid demo orders |
| `POST /simulation/pa/payment_disputes/create` | The bank opens disputes (A and B at RFI, C at CHARGEBACK) |
| `GET /pa/payment_disputes` | Reading the queue |
| `POST /files/upload` (files host) | Uploading A's evidence PDF |
| `POST /pa/payment_disputes/{id}/challenge` | Challenging A with `PURCHASE_HISTORY` and the evidence file |
| `POST /pa/payment_disputes/{id}/accept` | Accepting B (`LOW_VALUE_TRANSACTION` + refund) and A after the rejection |
| `POST /simulation/pa/payment_disputes/{id}/escalate` | The bank rejects A's evidence |
| `POST /simulation/pa/payment_disputes/{id}/resolve` | Final ruling, for disputes still being argued |
| `GET /pa/refunds` | Confirming B's refund and the double-refund guard |

## Running it

### 1. Install
```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure `.env`
```env
AWX_CLIENT_ID=...
AWX_API_KEY=...            # scoped sandbox key
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-sonnet-5-5
```
Scoped key permissions: **Payment Acceptance** (read/write), **Payment Disputes** (read/write), **Simulations** (write), **Upload Files** (write, global), optionally **Balances** (read).

### 3. Fresh data
```bash
python -m records.reset
```
Then create and pay three USD payment links ($1,240 / $18 / $340) with test card `4035501000000008`, any future expiry and CVC. (We used the Airwallex developer MCP to create the links.)

### 4. Run the demo 
```bash
python -m streamlit run app.py
```

### Tests
```bash
python -m pytest -v
```
13 tests cover every decision rule (including the rejection and deadline cases) and the approval binding.

## Sandbox notes

- **Card confirmation:** confirming a payment intent with raw card details returned *"not enabled for native API access"* on our account. The demo payments are made through Airwallex-hosted **payment links** instead, so our server never handles card numbers. `merchant/payments.py` keeps the direct create-and-confirm version for accounts with native access.
- **Dates:** the challenge endpoint needs `+00:00` offsets; the simulation endpoints accept `+0000`.
- **Refunds:** a refund can only be attached to an accept at the RFI stage, so case B is opened at RFI.
- **Final ruling:** the sandbox only resolves disputes that are still being argued; an accepted dispute returns *"Dispute transition is not supported"*.
- **Fees:** the sandbox doesn't charge dispute fees, so they're applied in code.

## Tech stack

Python 3.12 · Airwallex Sandbox API · Anthropic SDK (Claude, typed tool use) · requests · streamlit · fpdf2 · pytest · python-dotenv 

## What's next

- Win-rate weights learned from the merchant's own dispute history
- A "person overrides the agent" path: fight on to arbitration and receive the final ruling
- Webhooks instead of polling for dispute status changes