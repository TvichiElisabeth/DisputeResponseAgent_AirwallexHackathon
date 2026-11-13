"""Display data for the templates. Every number comes from the policy or Airwallex;
this module only formats it. No decisions are made here."""
import re
from datetime import datetime, timezone

from merchant.policy import (AUTO_APPROVE_LIMIT, MIN_CHALLENGE_PROB, URGENT_DAYS, Decision,
                             _parse_time)

ACTION_TONE = {"CHALLENGE": "blue", "ACCEPT": "green", "ESCALATE": "amber"}
VERDICT = {"CHALLENGE": "Challenge", "ACCEPT": "Accept", "ESCALATE": "Escalate"}
VERDICT_LINE = {
    "CHALLENGE": "Fight it: the evidence makes it worth the fee.",
    "ACCEPT": "Let it go: fighting costs more than it's likely to win.",
    "ESCALATE": "A person decides: the rules say this isn't the agent's call.",
}
# Same verdicts after the bank's new information changed the plan.
VERDICT_LINE_REVISED = {
    "CHALLENGE": "Fight it: the evidence now makes it worth the fee.",
    "ACCEPT": "Let it go: fighting now costs more than it's likely to win.",
    "ESCALATE": "A person decides: the rules say this isn't the agent's call.",
}
ACT_KIND = {"CHALLENGE": "challenge", "ACCEPT": "accept", "ESCALATE": "escalate"}
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


def initials(email: str) -> str:
    """'j.marin@example.com' -> 'JM'; 'sam@x.com' -> 'SA'."""
    local = (email or "").split("@")[0]
    parts = [p for p in re.split(r"[._+\-]+", local) if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return local[:2].upper()


def deadline_bar(dl: dict, open_: bool) -> dict:
    """The header's deadline: '6d' / '5h', red under the policy's URGENT_DAYS,
    bar = time left out of 7 days. Closed cases show no number or bar."""
    if not open_:
        return {"open": False}
    if dl["passed"]:
        return {"open": True, "passed": True, "urgent": True, "date": dl["date"]}
    return {"open": True, "passed": False, "num": dl["label"].split(" ")[0], "urgent": dl["urgent"],
            "pct": round(min(max(dl["days"], 0) / 7, 1) * 100), "date": dl["date"]}


def case_header(row: dict, order: dict, claims: dict, claim_source: str, open_: bool,
                network: str = "Visa") -> dict:
    """Everything the case header shows, from the live dispute row and the order record."""
    claim = claims.get(row.get("reason_code") or "")
    return {
        "letter": row["case"],
        "stage": stage_title(row["stage"]),
        "currency": row["currency"],
        "amount": f"{float(row['amount']):,.2f}",
        "claim": {"text": claim, "source": claim_source} if claim else None,
        "customer": {"email": order["customer"], "initials": initials(order["customer"])},
        "order": {"id": order["order_id"], "product": order["product"]},
        "reason": {"type": row["reason_type"], "network": network, "code": row.get("reason_code")},
        "deadline": deadline_bar(deadline(row["due_at"]), open_),
    }


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


# ---------------- plan history (initial plan vs revised plan) ----------------

def clock(iso: str) -> str:
    """'2026-11-12T09:14:03+00:00' -> '09:14'."""
    return _parse_time(iso).strftime("%H:%M")


def stamp(iso: str, year: bool = False) -> str:
    """'12 Nov, 09:14' (or '12 Nov 2026, 09:14'), in UTC like the rest of the app."""
    t = _parse_time(iso)
    return f"{t.day} {t:%b}{' ' + str(t.year) if year else ''}, {t:%H:%M}"


def stage_title(stage: str) -> str:
    """RFI stays RFI; CHARGEBACK becomes Chargeback."""
    return stage if stage == "RFI" else stage_label(stage).capitalize()


def plan_line(s: dict, after_rejection: bool = False) -> str:
    """One line of reasoning with the numbers, for a plan snapshot."""
    p, ca, cc = pct(s["p_win"]), f"{s['cost_accept']:,.2f}", f"{s['cost_challenge']:,.2f}"
    lead = f"Evidence rejected, now at {stage_title(s['stage'])}. " if after_rejection else ""
    if s["action"] == "CHALLENGE":
        return f"{lead}{p} win chance; expected cost {cc} vs {ca} to accept."
    if s["action"] == "ACCEPT":
        req = s.get("required_p")
        if req is not None and s["p_win"] < req:
            return (f"{lead}Win chance {p}, under the {pct(req)} minimum; challenging is "
                    f"expected to cost {cc} vs {ca} to accept.")
        return f"{lead}Accepting costs {ca}; challenging is expected to cost {cc}."
    return f"{lead}A person decides: the rules say this isn't the agent's call."


def plan_who(s: dict) -> tuple[str, str]:
    """Who approves this plan, and the one-line reason (the policy's own rule)."""
    if s["action"] == "ESCALATE":
        return "A person", "Escalated by the rules"
    if not s["needs_human"]:
        return "Automatic", f"Under {s['currency']} {AUTO_APPROVE_LIMIT:,.0f}"
    if s["amount"] > AUTO_APPROVE_LIMIT:
        return "You", f"Over {s['currency']} {AUTO_APPROVE_LIMIT:,.0f}"
    return "You", "After a bank rejection" if s.get("rejected_before") else "Policy rule"


def plan_cell(s: dict, version: int, after_rejection: bool = False) -> dict:
    return {"version": version, "at": stamp(s["at"]), "action": s["action"],
            "kind": ACT_KIND[s["action"]], "line": plan_line(s, after_rejection),
            "p_win": pct(s["p_win"]), "cost_challenge": f"{s['cost_challenge']:,.2f}",
            "verdict": VERDICT[s["action"]]}


def revision(history: list[dict], rejection: dict | None) -> dict | None:
    """The bank's new information and the plan before and after it, or None when
    nothing new arrived since the first plan. Display only: both plans were made by
    the policy at the time; nothing is recomputed here."""
    if not rejection or not rejection.get("at") or len(history) < 2:
        return None
    before = [i for i, s in enumerate(history) if s["at"] < rejection["at"]]
    after = [i for i, s in enumerate(history) if s["at"] >= rejection["at"]]
    if not before or not after:
        return None
    i, j = before[-1], after[-1]
    v1, v2 = history[i], history[j]
    who, why = plan_who(v2)
    return {
        "v1": plan_cell(v1, i + 1), "v2": plan_cell(v2, j + 1, after_rejection=True),
        "changed": v1["action"] != v2["action"], "who": who, "who_why": why,
        "bank": {"at": rejection["at"], "time": clock(rejection["at"]),
                 "date": stamp(rejection["at"], year=True),
                 "from_stage": stage_title(rejection.get("from_stage") or v1["stage"]),
                 "stage": stage_title(rejection.get("stage") or v2["stage"])},
        "agent_time": clock(v2["at"]),
    }


def revised_nodes(rev: dict, flags, reason_type: str = "") -> list[dict]:
    """The two new timeline entries: the bank's rejection and the agent's re-read."""
    bank = {"who": "Cardholder’s bank (Visa)", "kind": "bank", "event": "rejected",
            "when": rev["bank"]["time"], "weight": "against", "new": True,
            "text": f"Rejected our evidence and moved the case to {rev['bank']['stage']}."}
    read = [f for f in (facts(flags) if flags is not None else [])
            if f[0] != "Refund issued" and not (f[0] == "Unanswered contacts" and f[1] == "0")]
    refund = [f for f in (facts(flags) if flags is not None else []) if f[0] == "Refund issued"]
    agent_facts = read + [("Bank decision", "evidence rejected"), ("Stage", rev["bank"]["stage"]),
                          ("Win chance", f"{rev['v2']['p_win']} (was {rev['v1']['p_win']})")] + refund
    agent = {"who": "Dispute Desk agent", "kind": "agent", "new": True, "weight": "agent",
             "when": f"Read everything again · {rev['agent_time']}", "facts": agent_facts, "text": ""}
    return [bank, agent]
