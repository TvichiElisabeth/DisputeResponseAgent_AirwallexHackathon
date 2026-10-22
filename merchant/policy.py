"""Decision rules. Pure code: no API calls, no model.
Same dispute + same evidence flags -> same decision, every time."""
from dataclasses import dataclass
from datetime import datetime, timezone

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


def _parse_time(s: str) -> datetime:
    # Airwallex uses both +0000 and +00:00; normalise to +00:00
    if len(s) >= 5 and s[-5] in "+-" and s[-3] != ":":
        s = s[:-2] + ":" + s[-2:]
    return datetime.fromisoformat(s)


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

    # Who must approve: computed once, before any rule
    needs_human = d.amount > AUTO_APPROVE_LIMIT or d.rejected_before

    def out(action, needs_human, rule):
        urgent = (needs_human or action == ESCALATE) and days_left < URGENT_DAYS
        return Decision(d.case, action, p, cost_accept, cost_challenge,
                        needs_human, days_left, rule, urgent)

    # Rule 1: defending costs more than the dispute itself
    if not d.rejected_before and d.amount <= DISPUTE_FEE:
        return out(ACCEPT, needs_human,
                   f"Fee ${DISPUTE_FEE:.0f} >= amount ${d.amount:.0f}: defending costs "
                   f"more than the dispute, even if we win.")

    # Rule 2: the merchant may be at fault, so a person decides
    if f.unanswered_contacts >= MERCHANT_FAULT_CONTACTS and not f.refund_issued:
        return out(ESCALATE, True,
                   f"Customer contacted support {f.unanswered_contacts} times with no reply "
                   f"and no refund issued: a refund may be owed. A person decides.")

    # Rule 3: expected cost, with a minimum win chance and enough time to prepare
    worth_challenging = p >= MIN_CHALLENGE_PROB and cost_challenge < cost_accept
    if worth_challenging and days_left < MIN_DAYS_TO_CHALLENGE and not evidence_ready:
        return out(ESCALATE, True,
                   f"Worth challenging (win chance {p:.0%}), but only {days_left} days are "
                   f"left and the evidence isn't prepared. A person decides now: rush the "
                   f"evidence or concede.")
    if worth_challenging:
        return out(CHALLENGE, needs_human,
                   f"Win chance {p:.0%}: expected cost ${cost_challenge:,.2f} if we "
                   f"challenge vs ${cost_accept:,.2f} if we accept.")
    return out(ACCEPT, needs_human,
               f"Win chance {p:.0%}: challenging is expected to cost "
               f"${cost_challenge:,.2f} vs ${cost_accept:,.2f} to accept.")