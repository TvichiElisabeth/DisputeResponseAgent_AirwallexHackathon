"""Display data for the templates. Every number comes from the policy or Airwallex;
this module only formats it. No decisions are made here."""
from datetime import datetime, timezone

from merchant.policy import MIN_CHALLENGE_PROB, URGENT_DAYS, Decision, _parse_time

ACTION_TONE = {"CHALLENGE": "blue", "ACCEPT": "green", "ESCALATE": "amber"}
VERDICT = {"CHALLENGE": "Challenge", "ACCEPT": "Accept", "ESCALATE": "Escalate"}
VERDICT_LINE = {
    "CHALLENGE": "Fight it: the evidence makes it worth the fee.",
    "ACCEPT": "Let it go: fighting costs more than it's likely to win.",
    "ESCALATE": "A person decides: the rules say this isn't the agent's call.",
}
KIND_INITIAL = {"bank": "V", "agent": "AI"}


def money(amount, currency: str = "USD") -> str:
    return f"{currency} {float(amount):,.2f}"


def days_left(due_at: str) -> float:
    return round((_parse_time(due_at) - datetime.now(timezone.utc)).total_seconds() / 86400, 1)


def deadline(due_at: str) -> dict:
    d = days_left(due_at)
    if d <= 0:
        label = "Passed"
    elif d < 1:
        label = f"{round(d * 24)}h left"
    else:
        label = f"{d:.0f}d left"
    return {"date": due_at[:10], "days": d, "label": label,
            "urgent": 0 < d < URGENT_DAYS, "passed": d <= 0}


def pct(x: float) -> str:
    return f"{x:.0%}"


def bar(d: Decision) -> dict | None:
    """The break-even line: our win chance against the bar it has to clear.
    Same test as policy rule 3; greyed out when another rule decided."""
    be, req, p = d.break_even_p, d.required_p, d.p_win
    if be is None:
        return None

    def pos(x: float) -> float:
        return round(max(0.0, min(x, 1.0)) * 100, 2)

    active = d.money_decided
    clears = p >= MIN_CHALLENGE_PROB and p > be
    if not active:
        headline = ("Not the deciding factor: a person decides this case for the reason "
                    f"above. For reference: need {pct(req)}, have {pct(p)}.")
    elif be >= 1:
        headline = (f"Can't break even: the fee is more than the amount at risk "
                    f"(break-even {pct(be)}). Our win chance: {pct(p)}.")
    else:
        headline = f"Need {pct(req)}, have {pct(p)}: {'clears the bar' if clears else 'below the bar'}."

    return {
        "headline": headline,
        "active": active,
        "tone": ("blue" if clears else "orange") if active else "grey",
        "on_scale": be < 1,
        "zone_left": pos(req),
        "be_left": pos(be),
        "min_left": pos(MIN_CHALLENGE_PROB),
        "dot_left": pos(p),
        "be_label": pct(be) if be < 1 else f"{pct(be)} (off the scale)",
        "min_label": pct(MIN_CHALLENGE_PROB),
        "p_label": pct(p),
    }


def facts(flags) -> list[tuple[str, str]]:
    yes = lambda b: "yes" if b else "no"
    return [
        ("Matching earlier orders", str(flags.prior_undisputed_matches)),
        ("Signed delivery", yes(flags.signed_delivery)),
        ("Delivery scan", yes(flags.delivery_scanned)),
        ("Unanswered contacts", str(flags.unanswered_contacts)),
        ("Refund issued", yes(flags.refund_issued)),
    ]


TERM_LABELS = [
    ("action", "Action"), ("action_detail", "Airwallex reason"), ("amount", "Amount"),
    ("counterparty", "Customer"), ("order_id", "Order"), ("product", "Product"),
    ("reason_code", "Visa reason code"), ("stage", "Stage"), ("evidence_file", "Evidence file"),
]


def terms_rows(terms: dict) -> list[tuple[str, str]]:
    rows = []
    for key, label in TERM_LABELS:
        value = terms.get(key)
        if value is None:
            continue
        if key == "amount":
            value = money(value, terms.get("currency", "USD"))
        rows.append((label, str(value)))
    return rows


def stage_label(stage: str) -> str:
    """RFI stays an acronym; CHARGEBACK becomes "chargeback"."""
    return stage if stage == "RFI" else stage.replace("_", " ").lower()


def thread(case: str, row: dict, events: list[dict], flags=None) -> list[dict]:
    """The evidence thread: the bank's claim at the top, the evidence as replies,
    and (after a review) what the agent read out of it at the bottom."""
    nodes = [{
        "who": "Issuing bank", "kind": "bank", "initial": "V", "when": "Opened the dispute",
        "weight": "claim",
        "text": (f"Visa {row['reason_code']} · {row['reason_type'].replace('_', ' ').lower()} · "
                 f"{money(row['amount'], row['currency'])} at stake. Stage: {stage_label(row['stage'])}."),
    }]
    for ev in events:
        nodes.append({**ev, "initial": ev["who"][:1].upper()})
    if flags is not None:
        nodes.append({"who": "Dispute Desk agent", "kind": "agent", "initial": "AI",
                      "when": "Read everything above", "weight": "agent", "facts": facts(flags),
                      "text": ""})
    return nodes
