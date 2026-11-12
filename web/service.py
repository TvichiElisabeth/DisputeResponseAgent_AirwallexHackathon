"""Glue between the web routes and the existing agent. No money rules live here:
every decision, guard and API call is the same code the terminal and Streamlit use.

- One lock around everything that reads or writes the state (pessimistic, in this
  process). Across containers the state backend's version check refuses stale saves
  (optimistic); each step is then retried once on fresh state.
- Printed output from the agent is captured into a persistent activity log.
- The latest review (the plan) is stored in state, so refreshes and tabs agree.
- Approve carries the fingerprint the person saw; it's checked against live data.
"""
import contextlib
import functools
import io
import threading
from dataclasses import asdict
from datetime import datetime, timezone

from bank.reject import reject_evidence
from bank.sandbox import AirwallexSandboxSimulator
from bank.seed import open_disputes
from core.client import AirwallexClient
from merchant import agent, refunds
from merchant.approvals import terms_shown
from merchant.drafter import check_draft
from merchant.policy import CHALLENGE, DISPUTE_FEE, ESCALATE, Decision, EvidenceFlags
from merchant.queue import read_queue
from merchant.record_payments import record_payments
from records import state as st
from records.evidence_text import EVIDENCE, EVIDENCE_THREAD, ORDERS
from web import view

NEW_INFO = "The issuing bank rejected our evidence and moved the case to CHARGEBACK."
ACTIVITY_LIMIT = 200

LOCK = threading.Lock()
_client: AirwallexClient | None = None


class ActionError(Exception):
    """A refused or failed action, with a message fit to show the person."""


def client() -> AirwallexClient:
    global _client
    if _client is None:
        _client = AirwallexClient()
    return _client


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------- state helpers (always load fresh: agent functions save their own copy) ----

def _web(state: dict) -> dict:
    return state.setdefault("web", {})


def _update_web(fn) -> None:
    state = st.load()
    fn(_web(state))
    st.save(state)


def _notice(text: str, kind: str = "info") -> None:
    _update_web(lambda w: w.__setitem__("notice", {"text": text, "kind": kind}))


def _log(label: str, text: str, error: str | None = None) -> None:
    def add(w):
        log = w.setdefault("activity", [])
        log.append({"at": _now(), "label": label, "text": text, "error": error})
        del log[:-ACTIVITY_LIMIT]
    _update_web(add)


def run_logged(label: str, fn, *args, **kwargs):
    """Run an existing function, capture what it prints into the activity log,
    and turn failures into ActionError with a readable message."""
    buf = io.StringIO()
    error = None
    with contextlib.redirect_stdout(buf):
        try:
            result = fn(*args, **kwargs)
        except st.StateConflict:
            raise                   # not a failure of the step: _retry_on_conflict reruns it
        except SystemExit as e:
            error = str(e)
        except Exception as e:  # keep the page usable; show the reason
            error = str(e) or type(e).__name__
    _log(label, buf.getvalue().strip(), error)
    if error:
        raise ActionError(error)
    return result


def _retry_on_conflict(notify: bool = True):
    """Optimistic locking across containers: if another container saved the state
    after this step loaded it, the save is refused (StateConflict). Rerun the whole
    step once on fresh state. Money calls stay safe on the rerun: they reuse their
    request_id, and approvals re-check the live dispute and the fingerprint."""
    def wrap(fn):
        @functools.wraps(fn)
        def run(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except st.StateConflict:
                pass
            try:
                return fn(*args, **kwargs)
            except st.StateConflict:
                if not notify:
                    raise
                with contextlib.suppress(st.StateConflict):
                    _notice("Someone else changed this at the same moment. "
                            "Reload the page and try again.", "error")
        return run
    return wrap


# ---------------- the stored review ----------------

def item_key(row: dict, decision: Decision) -> str:
    return f"{decision.case}-{row['id']}-{row['stage']}-{decision.action}"


def _serialize(it: dict) -> dict:
    return {"row": it["row"], "decision": asdict(it["decision"]),
            "flags": asdict(it["flags"]), "note": it["note"]}


def _deserialize(raw: dict) -> dict:
    return {"row": dict(raw["row"]), "decision": Decision(**raw["decision"]),
            "flags": EvidenceFlags(**raw["flags"]), "note": raw["note"]}


def _stored_item(state: dict, case: str) -> dict | None:
    for raw in _web(state).get("review", {}).get("items", []):
        if raw["row"]["case"] == case:
            return _deserialize(raw)
    return None


def _set_outcome(key: str, text: str, kind: str) -> None:
    _update_web(lambda w: w.setdefault("outcomes", {}).__setitem__(key, {"text": text, "kind": kind}))


def approval_for(state: dict, it: dict) -> tuple[dict, str] | None:
    """The terms and fingerprint shown on an approval card (None if no approval)."""
    d, row = it["decision"], it["row"]
    if d.action == CHALLENGE:
        detail = agent.CHALLENGE_REASON[row["reason_type"]]
        evidence = state.get("evidence_files", {}).get(d.case)
    elif d.action == "ACCEPT":
        detail, evidence = agent.accept_reason(d), None
    else:
        return None
    return terms_shown(row, d, detail, evidence)


# ---------------- actions ----------------

@_retry_on_conflict()
def seed() -> None:
    with LOCK:
        c = client()
        try:
            run_logged("Record payments", record_payments, c, st.load())
            run_logged("Open disputes", open_disputes, AirwallexSandboxSimulator(c), st.load())
        except ActionError as e:
            _notice(str(e), "error")
            return
        _update_web(lambda w: (w.pop("review", None), w.pop("outcomes", None)))
        _notice("Payments recorded and disputes opened. Run a review next.", "ok")


@_retry_on_conflict()
def reject_a() -> None:
    with LOCK:
        try:
            run_logged("Issuer rejects A", reject_evidence, client(), st.load(), "A")
        except ActionError as e:
            _notice(str(e), "error")
            return
        _update_web(lambda w: (w.pop("review", None), w.pop("outcomes", None)))
        _notice("The issuing bank rejected Case A's evidence. Review the queue again.", "info")


@_retry_on_conflict()
def review() -> None:
    """Same as Streamlit's review: plan, then act on what needs no person
    (escalations, accepts under the limit) and prepare evidence for challenges."""
    with LOCK:
        c = client()
        try:
            items, run_info = run_logged("Review", agent.plan_with_run, c, st.load(), NEW_INFO)
        except ActionError as e:
            _notice(f"Review failed: {e}", "error")
            return

        outcomes = {}
        for it in items:
            d, key = it["decision"], item_key(it["row"], it["decision"])
            try:
                if d.action == ESCALATE or not d.needs_human:
                    run_logged(f"Case {d.case}", agent.act, c, st.load(), it, lambda _: "y")
                    outcomes[key] = {"text": "Escalated to a person" if d.action == ESCALATE
                                     else "Completed automatically", "kind": "ok"}
                elif d.action == CHALLENGE:
                    run_logged(f"Case {d.case} evidence", agent.evidence_for, c, st.load(),
                               it["row"], it["flags"])
            except ActionError as e:
                outcomes[key] = {"text": f"Not completed: {e}", "kind": "error"}

        def store(w):
            w["review"] = {"at": _now(), "items": [_serialize(it) for it in items], "agent": run_info}
            w["outcomes"] = outcomes
        _update_web(store)
        if not items:
            _notice("No open disputes need a response.", "info")


@_retry_on_conflict()
def decide_approval(case: str, shown_fingerprint: str, approve: bool) -> None:
    """Approve or reject a proposed action. Refuses if the live terms no longer
    match the fingerprint the person was shown."""
    with LOCK:
        c = client()
        state = st.load()
        it = _stored_item(state, case)
        if not it:
            _notice("Nothing to approve: run a review first.", "error")
            return
        key = item_key(it["row"], it["decision"])

        live = next((r for r in read_queue(c, state) if r["case"] == case), None)
        stale = (not live or live["id"] != it["row"]["id"] or live["stage"] != it["row"]["stage"]
                 or live["status"] != "REQUIRES_RESPONSE")
        if not stale:
            it["row"] = {**it["row"], **live}           # live amount, stage, deadline
            shown = approval_for(st.load(), it)
            stale = shown is None or shown[1] != shown_fingerprint
        if stale:
            _set_outcome(key, "Refused: the terms changed since you viewed them, so this "
                              "approval is void. Run the review again.", "error")
            return

        try:
            run_logged(f"Case {case} {'approved' if approve else 'not approved'}",
                       agent.act, c, st.load(), it, (lambda _: "y") if approve else (lambda _: "n"))
        except ActionError as e:
            _set_outcome(key, f"Not completed: {e}", "error")
            return
        _set_outcome(key, "Approved and completed" if approve else "Not approved: no action taken",
                     "ok" if approve else "info")


@_retry_on_conflict()
def prepare_package(case: str) -> None:
    with LOCK:
        try:
            pkg = run_logged(f"Case {case} package", agent.prepare_package, client(), st.load(), case)
        except ActionError as e:
            _notice(f"Could not prepare Case {case}: {e}", "error")
            return
        if pkg is None:
            _notice(f"No package for Case {case}: a person decides it directly.", "info")


def gate(case: str, subject: str, body: str, ticked: list[str]) -> dict:
    """Live check of the escalation form: reply problems and whether Approve is enabled."""
    item = st.load().get("human_queue", {}).get(case) or {}
    pkg = item.get("package") or {}
    checks = item.get("what_to_check", [])
    problems = check_draft(subject, body, float(item.get("amount", 0)), pkg.get("stage", ""))
    valid = {t for t in ticked if t.isdigit() and int(t) < len(checks)}
    all_ticked = len(valid) == len(checks)
    return {"case": case, "problems": problems, "all_ticked": all_ticked,
            "ready": all_ticked and not problems}


@_retry_on_conflict()
def resolve(case: str, subject: str, body: str, ticked: list[str]) -> None:
    with LOCK:
        g = gate(case, subject, body, ticked)
        if not g["all_ticked"]:                      # enforced here too, not only in the browser
            _notice(f"Case {case}: tick every check before approving.", "error")
            return
        try:
            run_logged(f"Case {case} resolved", agent.resolve_escalation, client(), st.load(),
                       case, subject, body, ask=lambda _: "y")
        except ActionError as e:
            _notice(f"Case {case} not completed: {e}", "error")
            return
        _notice(f"Case {case} accepted. The reply is ready to send.", "ok")


def keep_investigating(case: str) -> None:
    _notice(f"Case {case} stays in the queue. Nothing was changed.", "info")


# ---------------- the page ----------------

@_retry_on_conflict(notify=False)
def page() -> dict:
    """Everything the dashboard shows, from live Airwallex data plus state."""
    with LOCK:
        c = client()
        state = st.load()
        notice = _web(state).pop("notice", None)
        st.save(state)

        try:
            rows = read_queue(c, state)
        except KeyError:
            return {"has_disputes": False, "notice": notice,
                    "activity": list(reversed(_web(state).get("activity", [])))[:40]}

        web = _web(state)
        actions_log = state.get("actions", {})
        waiting = state.get("human_queue", {})
        resolved = state.get("resolved_escalations", {})
        outcomes = web.get("outcomes", {})

        def challenged(row):
            return any(op.startswith(f"challenge_{row['case']}_{row['id']}_") for op in actions_log)

        open_rows = [r for r in rows if r["status"] == "REQUIRES_RESPONSE" and r["case"] not in waiting]
        fees = sum(DISPUTE_FEE for r in rows if challenged(r))

        # Review cards
        proposed = {}
        cards = []
        for raw in web.get("review", {}).get("items", []):
            it = _deserialize(raw)
            d, row = it["decision"], it["row"]
            key = item_key(row, d)
            proposed[d.case] = d.action
            outcome = outcomes.get(key)
            approval = None
            if d.needs_human and d.action != ESCALATE and not outcome:
                shown = approval_for(state, it)
                if shown:
                    approval = {"rows": view.terms_rows(shown[0]), "fingerprint": shown[1],
                                "evidence_sha": (shown[0].get("evidence_sha256") or "")[:12]}
            if d.action == CHALLENGE:
                typed = agent.CHALLENGE_REASON[row["reason_type"]]
            elif d.action == "ACCEPT":
                typed = agent.accept_reason(d)
            else:
                typed = "No API action: handed to a person"
            cards.append({
                "case": d.case, "amount": view.money(row["amount"], row["currency"]),
                "action": d.action, "tone": view.ACTION_TONE[d.action], "urgent": d.urgent,
                "reason_code": row["reason_code"], "reason_type": row["reason_type"],
                "stage": row["stage"], "days_left": d.days_left, "p_win": view.pct(d.p_win),
                "typed": typed, "rule": d.rule, "bar": view.bar(d), "facts": view.facts(it["flags"]),
                "evidence": EVIDENCE.get(d.case, ""), "explanation": it["note"]["explanation"],
                "checks": it["note"].get("what_to_check", []),
                "cost_accept": f"{d.cost_if_accept:,.2f}",
                "cost_challenge": f"{d.expected_cost_if_challenge:,.2f}",
                "cheaper": "challenge" if d.expected_cost_if_challenge < d.cost_if_accept else "accept",
                "verdict": view.VERDICT[d.action], "verdict_line": view.VERDICT_LINE[d.action],
                "customer": ORDERS[d.case]["customer"], "product": ORDERS[d.case]["product"],
                "deadline": view.deadline(row["due_at"]),
                "thread": view.thread(d.case, row, EVIDENCE_THREAD.get(d.case, []), it["flags"]),
                "outcome": outcome, "approval": approval,
            })

        # Queue table
        queue = [{
            "case": r["case"], "amount": view.money(r["amount"], r["currency"]),
            "reason_code": r["reason_code"], "reason_type": r["reason_type"],
            "stage": r["stage"], "status": r["status"], "deadline": view.deadline(r["due_at"]),
            "proposed": proposed.get(r["case"]),
            "tone": view.ACTION_TONE.get(proposed.get(r["case"]), "grey"),
            "customer": ORDERS[r["case"]]["customer"], "product": ORDERS[r["case"]]["product"],
            "waiting": r["case"] in waiting, "resolved": r["case"] in resolved,
        } for r in sorted(rows, key=lambda r: r["due_at"])]

        # Escalations waiting for a person
        escalations = []
        row_by_case = {r["case"]: r for r in rows}
        for case, item in waiting.items():
            pkg = item.get("package")
            entry = {"case": case, "amount": view.money(item["amount"], item["currency"]),
                     "customer": item["counterparty"], "order": item["order_id"],
                     "deadline": view.deadline(item["due_at"]), "reason": item["reason"],
                     "explanation": item["explanation"], "checks": item["what_to_check"],
                     "thread": view.thread(case, {"reason_code": row_by_case.get(case, {}).get("reason_code", ""),
                                                  "reason_type": row_by_case.get(case, {}).get("reason_type", ""),
                                                  "amount": item["amount"], "currency": item["currency"],
                                                  "stage": row_by_case.get(case, {}).get("stage", "")},
                                           EVIDENCE_THREAD.get(case, [])),
                     "package": None}
            if pkg:
                plan_ = pkg["resolution"]
                draft = pkg["draft"]
                entry["package"] = {
                    "plan": plan_, "refund_text": (f"Refund {view.money(plan_['refund_amount'], item['currency'])}"
                                                   if plan_["should_refund"] else "No separate refund"),
                    "draft": draft, "evidence": EVIDENCE.get(case, ""),
                    "gate": gate(case, draft["subject"], draft["body"], []),
                }
            escalations.append(entry)

        resolved_list = [{
            "case": case, "amount": view.money(item["amount"], item["currency"]),
            "plan": item["resolution"], "by": item["resolved_by"],
            "at": item["resolved_at"][:16].replace("T", " "),
            "reply": f"Subject: {item['reply']['subject']}\n\n{item['reply']['body']}",
        } for case, item in resolved.items()]

        # Outcomes and money
        refunded = conceded = 0.0
        outcome_rows = []
        for r in rows:
            back = refunds.refunded_amount(c, state["payments"][r["case"]]["id"])
            if r["case"] in waiting:
                label, tone = "Waiting for a person", "amber"
            elif back:
                label, tone = f"Refunded {view.money(back, r['currency'])}", "green"
                refunded += back
            elif r["case"] in resolved:
                label, tone = "Accepted: customer was right (no separate refund)", "green"
                conceded += float(r["amount"])
            elif r["status"] == "ACCEPTED":
                label, tone = "Conceded", "grey"
                conceded += float(r["amount"])
            else:
                label, tone = "Open", "blue"
            outcome_rows.append({"case": r["case"], "amount": view.money(r["amount"], r["currency"]),
                                 "status": f"{r['stage']} / {r['status']}",
                                 "fee": f"{DISPUTE_FEE if challenged(r) else 0:,.2f}",
                                 "label": label, "tone": tone})

        return {
            "has_disputes": True, "notice": notice,
            "metrics": {"open": len(open_rows),
                        "at_stake": f"{sum(float(r['amount']) for r in open_rows):,.2f}",
                        "waiting": len(waiting), "fees": f"{fees:,.2f}"},
            "queue": queue, "cards": cards, "review_at": web.get("review", {}).get("at"),
            "agent_run": web.get("review", {}).get("agent"),   # plan summary, disagreements, trace
            "escalations": escalations, "resolved": resolved_list,
            "outcomes": outcome_rows,
            "totals": {"refunded": f"{refunded:,.2f}", "conceded": f"{conceded:,.2f}",
                       "fees": f"{fees:,.2f}"},
            "activity": list(reversed(web.get("activity", [])))[:40],
            "fee": f"{DISPUTE_FEE:,.0f}",
            "review_steps": [{"case": r["case"], "product": ORDERS[r["case"]]["product"]}
                             for r in sorted(open_rows, key=lambda r: r["due_at"])],
        }
