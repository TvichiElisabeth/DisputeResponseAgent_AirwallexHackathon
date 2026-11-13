"""Display data for the templates. Every number comes from the policy or Airwallex;
this module only formats it. No decisions are made here."""
import json
import math
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


def plan_why(s: dict, after_rejection: bool = False) -> str:
    """One short line of reasoning for a plan snapshot. The numbers sit above it
    in the panel, so the line doesn't repeat them."""
    ca = f"{s['cost_accept']:,.2f}"
    lead = f"Evidence rejected, now at {stage_title(s['stage'])}. " if after_rejection else ""
    on = " on" if after_rejection else ""
    if s["action"] == "CHALLENGE":
        return f"{lead}Fighting{on} is expected to cost less than refunding {ca}."
    if s["action"] == "ACCEPT":
        if s["cost_challenge"] > s["cost_accept"]:
            return f"{lead}Fighting{on} is expected to cost more than refunding."
        return f"{lead}The win chance is under the minimum needed to fight."
    return f"{lead}A person decides: the rules say this isn't the agent's call."


def plan_nums(s: dict) -> list[tuple[str, str]]:
    """The two key numbers of a plan, as (value, label)."""
    p, ca, cc = pct(s["p_win"]), f"{s['cost_accept']:,.2f}", f"{s['cost_challenge']:,.2f}"
    if s["action"] == "CHALLENGE":
        return [(p, "win chance"), (cc, "expected cost to challenge")]
    if s["action"] == "ACCEPT":
        req = s.get("required_p")
        return [(p, f"win chance · min {pct(req)}" if req is not None else "win chance"),
                (cc, f"to challenge vs {ca} to accept")]
    return [(p, "win chance"), (f"{s['amount']:,.2f}", "at stake")]


def plan_who(s: dict) -> dict:
    """Who approves this plan, and the one-line reason (the policy's own rule)."""
    limit = f"{s['currency']} {AUTO_APPROVE_LIMIT:,.0f}"
    if s["action"] == "ESCALATE":
        return {"name": "A person", "why": "Escalated by the rules", "auto": False}
    if not s["needs_human"]:
        return {"name": "Automatic", "why": f"Under {limit}, approved by the rules", "auto": True}
    if s["amount"] > AUTO_APPROVE_LIMIT:
        return {"name": "You", "why": f"Over {limit}, so a person approves", "auto": False}
    why = "After a bank rejection, so a person approves" if s.get("rejected_before") \
        else "A policy rule asks for a person"
    return {"name": "You", "why": why, "auto": False}


def plan_cell(s: dict, version: int, after_rejection: bool = False) -> dict:
    return {"version": version, "at": stamp(s["at"]), "iso": s["at"], "action": s["action"],
            "run_id": s.get("run_id"),
            "kind": ACT_KIND[s["action"]], "why": plan_why(s, after_rejection),
            "nums": plan_nums(s), "p_win": pct(s["p_win"]),
            "cost_challenge": f"{s['cost_challenge']:,.2f}", "verdict": VERDICT[s["action"]]}


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
    return {
        "v1": plan_cell(v1, i + 1), "v2": plan_cell(v2, j + 1, after_rejection=True),
        "changed": v1["action"] != v2["action"], "approver": plan_who(v2),
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


# ---------------- agent runs (the drawer on the case page) ----------------

KIND_LABEL = {"invoke_agent": "invoke_agent", "execute_tool": "execute_tool", "chat": "chat"}


def case_spans(spans: list[dict], case: str) -> list[dict]:
    """This case's spans plus the shared ones (the agent span, model turns,
    list_open_disputes, submit_plan): spans with no case belong to every case."""
    return [s for s in spans if s.get("case") in (None, case)]


def duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 60:
        return f"{seconds:.1f} s"
    return f"{int(seconds // 60)} m {seconds % 60:02.0f} s"


def pretty(value) -> str:
    """A span's stored input/output, pretty-printed when it's JSON."""
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return value
    return json.dumps(value, indent=2, ensure_ascii=False)


def run_versions(history: list[dict]) -> dict[str, int]:
    """run_id -> the plan version it produced, for one case."""
    return {h["run_id"]: i + 1 for i, h in enumerate(history) if h.get("run_id")}


def run_tabs(runs: list[dict], history: list[dict], case: str) -> list[dict]:
    """One tab per kept run that reviewed this case, oldest first."""
    versions = run_versions(history)
    tabs = []
    for r in runs:
        if case not in (r.get("outcomes") or {}):
            continue
        v = versions.get(r["id"])
        when = stamp(r.get("started_at") or r["at"])
        tabs.append({"id": r["id"], "version": v, "steps": len(case_spans(r.get("spans", []), case)),
                     "label": f"Run v{v} · {when}" if v else f"Run · {when}"})
    return tabs


def disagreements_for(run: dict, case: str) -> list[dict]:
    """Where the model's proposal for this case differed from the policy, as two
    sides and what the code did about it (the policy applies; a person approves)."""
    out = []
    for it in run.get("plan_items", []):
        if it.get("case") != case or it.get("agrees", True):
            continue
        out.append({"a": "Agent proposed", "av": f"{VERDICT.get(it['action'], it['action'])}. {it.get('reason', '')}".strip(),
                    "b": "Policy (code)",
                    "bv": f"{VERDICT.get(it['policy_action'], it['policy_action'])}, from the verified facts",
                    "res": "The policy applies, and a person must approve before anything moves."})
    return out


def agent_run(run: dict, case: str) -> dict:
    """Everything the drawer shows for one run, for one case."""
    spans = case_spans(run.get("spans", []), case)
    total = run.get("duration_s") or max((s["start_s"] + s["dur_s"] for s in spans), default=0) or 1
    action = (run.get("outcomes") or {}).get(case)
    rows = []
    for s in spans:
        left = max(0.0, min(s["start_s"] / total, 1.0)) * 100
        width = max(min(s["dur_s"] / total * 100, 100 - left), 0.6)
        rows.append({
            "id": s["id"], "name": s["name"], "kind": s["kind"], "depth": s.get("depth", 0),
            "case": s.get("case"), "error": s.get("error", False),
            "dur": duration(s["dur_s"]), "started": f"+{duration(s['start_s'])}" if s["start_s"] else "0 ms",
            "bar_left": round(left, 2), "bar_width": round(width, 2),
            "input": pretty(s.get("input")), "output": pretty(s.get("output")),
        })
    return {
        "id": run["id"], "case": case, "trigger": run.get("trigger") or "—",
        "duration": duration(run.get("duration_s")), "steps": len(spans),
        "model": run.get("model") or "—", "summary": run.get("summary") or "The model submitted no plan summary.",
        "finished": run.get("finished"), "stop": run.get("stop", ""),
        "outcome": VERDICT.get(action, "—") if action else "—", "outcome_kind": ACT_KIND.get(action, "none"),
        "disagreements": disagreements_for(run, case), "spans": rows,
    }


# ---------------- ring charts (fees paid / fees avoided) ----------------

CASE_COLOR = {"A": "#00a2c7", "B": "#1a1a1a", "C": "#0052ff"}   # same colour per case in every ring
RING_R = 84
RING_H = 250
LABEL_GAP = 56          # ring edge to the label column


def _wrap(text: str, width: int = 30, max_lines: int = 2) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;") + "…"
    return lines


def _anchor_deg(start: float, end: float) -> float:
    """Where a callout's dot sits on its arc (degrees clockwise from 12 o'clock):
    the middle, except a big arc anchors at 3 or 9 o'clock so its label sits beside the ring."""
    if end - start > 90:
        for a in (90.0, 270.0):
            if start + 8 <= a <= end - 8:
                return a
    return (start + end) / 2


def ring(total: float, parts: list[dict], extras: list[dict], centre: dict, aria: str) -> dict:
    """Geometry for one ring chart. Display only: the amounts come from the caller.

    parts: arcs in order from 12 o'clock, clockwise: {value, color (None = grey track,
           no slice), title (tooltip), callout (dict or None)}.
    extras: callouts with no arc (e.g. a case not counted): drawn bottom-left, no dot.
    callout: {tile, title, amount, pct, reason, muted}.
    pathLength = total, so each slice's dash length is its amount."""
    circ = 2 * math.pi * RING_R
    total = total if total > 0 else 1.0
    gap = 3 * total / circ                  # ~3px between slices, in amount units
    min_dash = 2 * total / circ

    slices, pending = [], []
    start = 0.0
    for p in parts:
        v = float(p["value"])
        if p.get("color") and v > 0:
            dash = max(v - gap, min_dash)
            slices.append({"color": p["color"], "dash": round(dash, 3), "rest": round(total - dash, 3),
                           "offset": round(-(start + gap / 2), 3), "title": p.get("title", "")})
        if p.get("callout") and v > 0:
            a = _anchor_deg(start / total * 360, (start + v) / total * 360)
            pending.append({**p["callout"], "deg": a, "side": 1 if math.sin(math.radians(a)) >= 0 else -1,
                            "dot_color": p.get("color") or "#d6d6d4"})
        start += v
    for e in extras:
        pending.append({**e, "deg": None, "side": -1, "dot_color": None})

    # Labels on both sides: a wide chart. Right side only: a compact one, with the
    # label column closer to the ring and shorter lines, so text stays inside the SVG.
    wide = any(c["side"] < 0 for c in pending)
    w, cx, cy = (760, 380, RING_H / 2) if wide else (400, 140, RING_H / 2)
    label_gap, wrap_at = (LABEL_GAP, 32) if wide else (26, 20)
    h = RING_H

    callouts = []
    for c in pending:
        if c["deg"] is None:
            dot, ly = None, cy + 68
        else:
            rad = math.radians(c["deg"])
            dot = (round(cx + RING_R * math.sin(rad), 1), round(cy - RING_R * math.cos(rad), 1))
            if abs(dot[1] - cy) < 30:
                ly = dot[1] + 5                    # straight leader
            elif dot[1] < cy:
                ly = dot[1] - 15
            else:
                ly = dot[1] + 20
        reasons = _wrap(c.get("reason") or "", wrap_at)
        lines = 1 + (1 if c.get("amount") else 0) + len(reasons)
        callouts.append({**c, "dot": dot, "ly": max(27.0, ly), "reasons": reasons,
                         "height": 17 + 4 + 20 * (lines - 1) + (6 if c.get("amount") else 0)})

    for side in (1, -1):                         # labels on one side never overlap
        col = sorted((c for c in callouts if c["side"] == side), key=lambda c: c["ly"])
        bottom = 0.0
        for c in col:
            c["ly"] = max(c["ly"], bottom + 14 + 17)
            bottom = c["ly"] - 17 + c["height"]
            h = max(h, bottom + 8)

    for c in callouts:
        side, ly = c["side"], c["ly"]
        col_x = cx + side * (RING_R + label_gap)
        if c.get("tile"):
            tx = col_x + 8 if side > 0 else col_x - 8 - 24
            c["tile_box"] = {"x": tx, "y": ly - 17, "cx": tx + 12}
            c["title_x"], c["text_x"] = (tx + 32, tx) if side > 0 else (tx - 12, tx + 24)
        else:
            c["tile_box"] = None
            c["title_x"] = c["text_x"] = col_x + side * 6
        c["anchor"] = "start" if side > 0 else "end"
        c["amount_y"] = ly + 27
        first = ly + (47 if c.get("amount") else 27)
        c["reason_lines"] = [{"y": first + 16 * i, "text": t} for i, t in enumerate(c["reasons"])]
        if c["dot"]:
            dx, dy = c["dot"]
            line_y = ly - 5
            if abs(line_y - dy) < 2:
                c["path"] = f"M{dx + side * 6:.1f} {dy:.1f}H{col_x:.1f}"
            else:                                # bend, never past the label column
                bend = min(27.0, max(9.0, abs(col_x - dx) / 2))
                c["path"] = (f"M{dx + side * 5:.1f} {dy + (-5 if line_y < dy else 5):.1f}"
                             f"L{dx + side * bend:.1f} {line_y:.1f}H{col_x:.1f}")
        else:
            c["path"] = None

    return {"w": w, "h": round(h), "cx": cx, "cy": cy, "r": RING_R, "total": round(total, 2),
            "slices": slices, "callouts": callouts, "centre": centre, "aria": aria}
