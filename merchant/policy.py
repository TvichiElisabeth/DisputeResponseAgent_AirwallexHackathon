"""Decision rules. Pure code: no API calls, no model.
Same dispute + same evidence flags -> same decision, every time."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

# ---- Demo economics (synthetic, configure per merchant) ----
DISPUTE_FEE = 25.00          # paid when we defend, win or lose (sandbox doesn't charge it)
ARBITRATION_FEE = 500.00     # cost of fighting on after the issuer rejects our evidence
AUTO_APPROVE_LIMIT = 50.00   # above this amount, a person approves the action
MIN_CHALLENGE_PROB = 0.50    # don't fight weak cases: losses hurt our win rate
REJECTION_FACTOR = 0.40      # issuer already said no once: win chance drops
COMPELLING_MATCHES = 2       # Visa CE 3.0 style: 2+ prior undisputed orders, same device + IP
MERCHANT_FAULT_CONTACTS = 2  # unanswered customer contacts that make it a human call
MIN_DAYS_TO_CHALLENGE = 2    # less time than this: no time to prepare and submit evidence
URGENT_DAYS = 3              # a person is needed and less time than this: flag URGENT

ACCEPT, CHALLENGE, ESCALATE = "ACCEPT", "CHALLENGE", "ESCALATE"

# Airwallex dispute stages this module reasons about
DisputeStage = Literal["RFI", "CHARGEBACK", "PRE_ARBITRATION", "ARBITRATION"]


@dataclass(frozen=True)
class EvidenceFlags:
    """Typed facts extracted from the evidence (by the model, later)."""
    prior_undisputed_matches: int = 0   # earlier orders, same device AND IP, not disputed
    signed_delivery: bool = False
    delivery_scanned: bool = False
    unanswered_contacts: int = 0
    refund_issued: bool = False


@dataclass(frozen=True)
class Dispute:
    case: str
    amount: float
    currency: str
    reason_type: str          # Airwallex reason.type, e.g. FRAUDULENT
    stage: str
    status: str
    due_at: str
    rejected_before: bool = False


@dataclass(frozen=True)
class Decision:
    case: str
    action: str
    p_win: float
    cost_if_accept: float
    expected_cost_if_challenge: float
    needs_human: bool
    days_left: float
    rule: str
    urgent: bool = False
    # Break-even line (display only; the rules above already decided):
    break_even_p: float | None = None   # win chance where challenging costs the same as accepting
    required_p: float | None = None     # the bar to clear: higher of break-even and MIN_CHALLENGE_PROB
    money_decided: bool = True          # False when another rule (merchant fault, deadline) decided


def _parse_time(s: str) -> datetime:
    # Airwallex uses both +0000 and +00:00; normalise to +00:00
    if len(s) >= 5 and s[-5] in "+-" and s[-3] != ":":
        s = s[:-2] + ":" + s[-2:]
    return datetime.fromisoformat(s)


def merchant_at_fault(f: EvidenceFlags) -> bool:
    """Rule 2's test: the customer kept asking, nobody answered, and no refund went out."""
    return f.unanswered_contacts >= MERCHANT_FAULT_CONTACTS and not f.refund_issued


def win_probability(reason_type: str, f: EvidenceFlags) -> float:
    """Demo scoring, not real statistics. Which evidence counts depends on the claim."""
    if reason_type == "FRAUDULENT":
        p = 0.15
        if f.prior_undisputed_matches >= COMPELLING_MATCHES:
            p += 0.55
        if f.signed_delivery:
            p += 0.15
    elif reason_type == "PRODUCT_NOT_RECEIVED":
        p = 0.10
        if f.delivery_scanned:
            p += 0.25
        if f.signed_delivery:
            p += 0.45
    elif reason_type == "CREDIT_NOT_PROCESSED":
        p = 0.30
        if f.refund_issued:
            p += 0.50
        if f.unanswered_contacts:
            p -= 0.20
    else:
        p = 0.20
    return round(min(max(p, 0.0), 0.95), 2)


def decide(d: Dispute, f: EvidenceFlags, now: datetime | None = None,
           evidence_ready: bool = False) -> Decision:
    now = now or datetime.now(timezone.utc)

    # ---- state guards ----
    if d.status != "REQUIRES_RESPONSE":
        raise ValueError(f"[{d.case}] status is {d.status}; nothing to decide.")
    days_left = round((_parse_time(d.due_at) - now).total_seconds() / 86400, 1)
    if days_left <= 0:
        raise ValueError(f"[{d.case}] deadline passed ({d.due_at}).")

    # ---- economics ----
    p = win_probability(d.reason_type, f)
    if d.rejected_before:
        p = round(p * REJECTION_FACTOR, 2)
        extra_cost = ARBITRATION_FEE      # the first fee is already spent (sunk)
    else:
        extra_cost = DISPUTE_FEE
    cost_accept = d.amount              # assumes the fee is charged only when we defend
    cost_challenge = round(extra_cost + (1 - p) * d.amount, 2)

    # Break-even: extra_cost + (1 - p) * amount < amount  <=>  p > extra_cost / amount.
    # Above 1.0 means no win chance can make challenging pay (the fee exceeds the amount).
    break_even = extra_cost / d.amount if d.amount > 0 else None
    required = max(break_even, MIN_CHALLENGE_PROB) if break_even is not None else None

    # Who must approve: computed once, before any rule
    needs_human = d.amount > AUTO_APPROVE_LIMIT or d.rejected_before

    def out(action, needs_human, rule, money_decided=True):
        urgent = (needs_human or action == ESCALATE) and days_left < URGENT_DAYS
        return Decision(d.case, action, p, cost_accept, cost_challenge,
                        needs_human, days_left, rule, urgent,
                        break_even, required, money_decided)

    # Rule 1: defending costs more than the dispute itself
    if not d.rejected_before and d.amount <= DISPUTE_FEE:
        return out(ACCEPT, needs_human,
                   f"Fee ${DISPUTE_FEE:.0f} >= amount ${d.amount:.0f}: defending costs "
                   f"more than the dispute, even if we win.")

    # Rule 2: the merchant may be at fault, so a person decides
    if merchant_at_fault(f):
        return out(ESCALATE, True,
                   f"Customer contacted support {f.unanswered_contacts} times with no reply "
                   f"and no refund issued: a refund may be owed. A person decides.",
                   money_decided=False)

    # Rule 3: expected cost, with a minimum win chance and enough time to prepare
    worth_challenging = p >= MIN_CHALLENGE_PROB and cost_challenge < cost_accept
    if worth_challenging and days_left < MIN_DAYS_TO_CHALLENGE and not evidence_ready:
        return out(ESCALATE, True,
                   f"Worth challenging (win chance {p:.0%}), but only {days_left} days are "
                   f"left and the evidence isn't prepared. A person decides now: rush the "
                   f"evidence or concede.",
                   money_decided=False)
    if worth_challenging:
        return out(CHALLENGE, needs_human,
                   f"Win chance {p:.0%}: expected cost ${cost_challenge:,.2f} if we "
                   f"challenge vs ${cost_accept:,.2f} if we accept.")
    return out(ACCEPT, needs_human,
               f"Win chance {p:.0%}: challenging is expected to cost "
               f"${cost_challenge:,.2f} vs ${cost_accept:,.2f} to accept.")

# ---- Resolving a "merchant may be at fault" escalation (rule 2) ----

@dataclass(frozen=True)
class ResolutionPlan:
    """What the agent proposes to the person. Decided here, in code; the model
    only writes the customer reply around it."""
    action: str                     # ACCEPT
    accept_reason: str              # Airwallex accept enum
    should_refund: bool             # attach a refund to the accept?
    refund_amount: float            # 0.0 when no refund
    refund_reason: str | None       # Airwallex refund enum, when refunding
    explanation: str                # plain-language reason, shown on the card


def resolution_for(dispute: Dispute, stage: DisputeStage) -> ResolutionPlan:
    """dispute: the escalated case. stage: its LIVE stage, re-read from Airwallex
    right before proposing or acting (it may have moved since the escalation).

    The stage decides the refund: at RFI the money hasn't moved, so the refund is
    how the customer is paid back. At CHARGEBACK the bank has already returned the
    money, so a refund on top would pay the customer twice."""
    amount = f"{dispute.currency} {dispute.amount:,.2f}"
    if stage == "RFI":
        return ResolutionPlan(
            ACCEPT, "VALID_CUSTOMER_DISPUTE", True, dispute.amount, "REQUESTED_BY_CUSTOMER",
            f"Accept and refund {amount}: at RFI the money hasn't moved yet, so the refund "
            f"is how the customer gets it back.")
    if stage == "CHARGEBACK":
        return ResolutionPlan(
            ACCEPT, "VALID_CUSTOMER_DISPUTE", False, 0.0, None,
            f"Accept, with no separate refund: at chargeback the bank already returned "
            f"{amount} to the customer. Refunding again would pay them twice.")
    raise ValueError(f"[{dispute.case}] no automatic resolution at stage {stage}; "
                     f"a person handles it directly.")
