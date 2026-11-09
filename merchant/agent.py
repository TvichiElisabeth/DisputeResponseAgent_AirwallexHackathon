"""The dispute agent.

For every open dispute (soonest deadline first):
  queue (Airwallex) -> reader (model: facts) -> policy (code: decision)
  -> explainer (model: why) -> PLAN printed for the finance lead
  -> act: approval if needed -> REST call, or escalate to a person.

Run it again after new information (e.g. the bank rejects our evidence):
cases already handled are skipped; changed cases are re-decided.
"""
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone

from core.client import AirwallexClient
from merchant import actions, drafter, evidence_files, refunds
from merchant.approvals import escalate, request_approval, verify_approval
from merchant.explainer import explain
from merchant.policy import (ACCEPT, CHALLENGE, DISPUTE_FEE, ESCALATE, Dispute, decide,
                             merchant_at_fault, resolution_for)
from merchant.queue import read_queue
from merchant.reader import read_evidence
from records import state as st
from records.evidence_text import EVIDENCE, ORDER_FACTS, ORDERS

# Typed reasons Airwallex records with each action (chosen in code, not by the model)
CHALLENGE_REASON = {
    "FRAUDULENT": "PURCHASE_HISTORY",
    "PRODUCT_NOT_RECEIVED": "PRODUCT_RECEIVED",
    "CREDIT_NOT_PROCESSED": "OTHER_REASONS",
}


def accept_reason(decision) -> str:
    return "LOW_VALUE_TRANSACTION" if decision.cost_if_accept <= DISPUTE_FEE else "OTHERS"


def open_cases(client, state) -> list[dict]:
    rows = read_queue(client, state)
    waiting = state.get("human_queue", {})
    rows = [r for r in rows if r["status"] == "REQUIRES_RESPONSE" and r["case"] not in waiting]
    return sorted(rows, key=lambda r: r["due_at"])          # soonest deadline first


def to_dispute(row: dict, state: dict) -> Dispute:
    return Dispute(row["case"], float(row["amount"]), row["currency"], row["reason_type"],
                   row["stage"], row["status"], row["due_at"],
                   rejected_before=row["case"] in state.get("rejections", {}))


def evidence_for(client, state, row, flags) -> dict:
    """Build + upload the PDF once per dispute; reuse it on reruns (stable hash)."""
    existing = state.get("evidence_files", {}).get(row["case"])
    if existing and existing.get("dispute_id") == row["id"]:
        return existing
    argument = (f"The cardholder made this purchase. {flags.prior_undisputed_matches} earlier "
                f"orders from the same customer used the same device fingerprint and IP "
                f"address and were not disputed.")
    if flags.signed_delivery:
        argument += " The order was delivered and signed for."
    path = evidence_files.build_pdf(row["case"], row, argument)
    record = evidence_files.upload(client, state, row["case"], path)
    record["dispute_id"] = row["id"]
    st.save(state)
    return record


def need_text(d) -> str:
    """Win chance needed to challenge, for the plan table ('-' when money didn't decide)."""
    if d.required_p is None or not d.money_decided:
        return "-"
    return ">100%" if d.required_p > 1 else f"{d.required_p:.0%}"


def print_plan(items: list[dict]) -> None:
    print("\nPLAN (soonest deadline first)")
    print(f"  {'case':<5}{'amount':>10}  {'action':<10}{'who':<11}{'days':>6}  {'win':>5}"
          f"  {'need':>6}  why")
    for it in items:
        d, row = it["decision"], it["row"]
        who = ("URGENT you" if d.urgent else "you") if d.needs_human or d.action == "ESCALATE" else "auto"
        print(f"  {d.case:<5}{row['currency']} {float(row['amount']):>6,.0f}  {d.action:<10}"
              f"{who:<11}{d.days_left:>6}  {d.p_win:>5.0%}  {need_text(d):>6}"
              f"  {it['note']['explanation']}")
    needs_you = [it["decision"].case for it in items if it["decision"].needs_human]
    print(f"\n  Approvals or decisions needed from you: {', '.join(needs_you) or 'none'}")


def act(client, state, it: dict, ask) -> None:
    row, d, flags, note = it["row"], it["decision"], it["flags"], it["note"]

    if d.action == ESCALATE:
        escalate(state, row, d, note["explanation"], note["what_to_check"])
        build_package(state, row, flags)       # ready-to-approve, if the merchant is at fault
        return

    if d.action == CHALLENGE:
        detail = CHALLENGE_REASON[row["reason_type"]]
        evidence = evidence_for(client, state, row, flags)
        approver = "dispute-agent (auto)"
        if d.needs_human:
            if not request_approval(state, row, d, detail, evidence, note["explanation"], ask=ask):
                print(f"[{d.case}] not approved; no action taken.")
                return
            approver = verify_approval(state, row, d, detail, evidence)
        actions.challenge(client, state, row, detail, evidence,
                          ORDER_FACTS.get(row["case"], {}), challenged_by=approver)
        return

    if d.action == ACCEPT:
        detail = accept_reason(d)
        refund_reason = None
        if row["stage"] == "RFI":                  # only RFI accepts carry a refund
            paid = state["payments"][row["case"]]["amount"]
            if not refunds.can_refund(client, row["payment_intent_id"], paid, paid):
                escalate(state, row, d, "A refund already exists for this payment.",
                         ["Confirm the existing refund reached the customer."])
                return
            refund_reason = "REQUESTED_BY_CUSTOMER"
        approver = "dispute-agent (auto, under limit)"
        if d.needs_human:
            if not request_approval(state, row, d, detail, None, note["explanation"], ask=ask):
                print(f"[{d.case}] not approved; no action taken.")
                return
            approver = verify_approval(state, row, d, detail, None)
        actions.accept(client, state, row, detail, d.rule, approver, refund_reason)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _reply_text(subject: str, body: str) -> str:
    """The exact customer message the approval is bound to."""
    return f"Subject: {subject.strip()}\n\n{body.strip()}"


def build_package(state, row: dict, flags) -> dict | None:
    """Turn a 'merchant may be at fault' escalation into a ready-to-approve package:
    the resolution (code), a checked draft reply (model), stored on the queue item.
    Built once; reruns reuse it. Other escalations (e.g. deadline) keep the checklist."""
    item = state.get("human_queue", {}).get(row["case"])
    if not item or not merchant_at_fault(flags):
        return None
    if item.get("package"):
        return item["package"]
    try:
        plan_ = resolution_for(to_dispute(row, state), row["stage"])
    except ValueError as e:
        print(f"[{row['case']}] no resolution package: {e}")
        return None
    draft = drafter.draft_reply(ORDERS[row["case"]], float(row["amount"]), row["currency"],
                                row["stage"], plan_, EVIDENCE[row["case"]])
    item["package"] = {"stage": row["stage"], "resolution": asdict(plan_),
                       "draft": draft, "at": _now()}
    st.save(state)
    refund = (f"refund {row['currency']} {plan_.refund_amount:,.2f}" if plan_.should_refund
              else "no separate refund")
    print(f"[{row['case']}] resolution package ready: {plan_.action} "
          f"({plan_.accept_reason}), {refund}; reply drafted by the {draft['source']}")
    return item["package"]


def prepare_package(client, state, case: str) -> dict | None:
    """Build the package for a case escalated earlier (e.g. before packages existed,
    or after the stage moved). Reads the live dispute and the cached evidence facts."""
    row = next(r for r in read_queue(client, state) if r["case"] == case)
    flags, _ = read_evidence(state, case, row["reason_type"])
    return build_package(state, row, flags)


def resolve_escalation(client, state, case: str, subject: str, body: str,
                       approver: str = "finance-ops-lead", ask=input) -> dict:
    """The person approved the package (possibly with an edited reply). Re-check
    everything against live data, bind the approval to the exact reply, then accept."""
    item = state.get("human_queue", {}).get(case)
    if not item or not item.get("package"):
        raise ValueError(f"[{case}] no prepared package to approve.")

    row = next(r for r in read_queue(client, state) if r["case"] == case)      # live
    if row["status"] != "REQUIRES_RESPONSE":
        raise ValueError(f"[{case}] is now {row['stage']} / {row['status']}: nothing to accept.")
    if row["stage"] != item["package"]["stage"]:
        item.pop("package")                     # proposed for another stage: build it again
        st.save(state)
        raise ValueError(f"[{case}] moved to {row['stage']} since the package was prepared. "
                         f"Prepare it again.")

    dispute = to_dispute(row, state)
    flags, _ = read_evidence(state, case, row["reason_type"])
    decision = decide(dispute, flags)           # state guards: closed or past the deadline
    plan_ = resolution_for(dispute, row["stage"])

    problems = drafter.check_draft(subject, body, float(row["amount"]), row["stage"])
    if problems:
        raise ValueError("Reply not accepted: " + " ".join(problems))
    reply = _reply_text(subject, body)

    if plan_.should_refund:                     # RFI only; never refund the same money twice
        paid = state["payments"][case]["amount"]
        intent = state["disputes"][case]["payment_intent_id"]
        if not refunds.can_refund(client, intent, plan_.refund_amount, paid):
            raise ValueError(f"[{case}] a refund already exists for this payment.")

    proposed = replace(decision, action=ACCEPT, rule=plan_.explanation)
    if not request_approval(state, row, proposed, plan_.accept_reason, None, plan_.explanation,
                            approver=approver, ask=ask, reply_text=reply):
        return {"approved": False}
    who = verify_approval(state, row, proposed, plan_.accept_reason, None, reply_text=reply)

    result = actions.accept(client, state, row, plan_.accept_reason,
                            description=plan_.explanation[:250], accepted_by=who,
                            refund_reason=plan_.refund_reason)

    resolved = state.setdefault("resolved_escalations", {})
    resolved[case] = {**item, "status": "RESOLVED", "resolved_by": who, "resolved_at": _now(),
                      "result": result, "resolution": asdict(plan_),
                      "reply": {"subject": subject.strip(), "body": body.strip(),
                                "status": "READY_TO_SEND"}}
    del state["human_queue"][case]
    st.save(state)
    print(f"[{case}] escalation resolved by {who}: {plan_.accept_reason}; "
          f"reply ready to send (not sent automatically)")
    return resolved[case]


def plan(client, state, new_information: str | None = None) -> list[dict]:
    """Think only: facts, decision and explanation for every open case. Changes nothing."""
    items = []
    for row in open_cases(client, state):
        row["payment_intent_id"] = state["disputes"][row["case"]]["payment_intent_id"]
        flags, summary = read_evidence(state, row["case"], row["reason_type"])
        prepared = state.get("evidence_files", {}).get(row["case"], {})
        decision = decide(to_dispute(row, state), flags,
                          evidence_ready=prepared.get("dispute_id") == row["id"])
        info = None
        if row["case"] in state.get("rejections", {}):
            challenged = any(op.startswith(f"challenge_{row['case']}_")
                             for op in state.get("actions", {}))
            info = new_information or "The issuing bank rejected our evidence."
            if challenged:
                info += " Our previous decision on this case was CHALLENGE."
        note = explain(decision, flags, summary, new_information=info)
        items.append({"row": row, "flags": flags, "decision": decision, "note": note})
    return items


def run(new_information: str | None = None, ask=input) -> list[dict]:
    client = AirwallexClient()
    state = st.load()
    items = plan(client, state, new_information)
    if not items:
        print("No open disputes need a response.")
        return items
    print_plan(items)
    for it in items:
        act(client, state, it, ask)
    return items


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Run the dispute agent over the open queue.")
    p.add_argument("--yes", action="store_true", help="auto-approve (rehearsals only)")
    p.add_argument("--new-info", default=None, help="what changed since the last run")
    args = p.parse_args()
    run(args.new_info, ask=(lambda _: "y") if args.yes else input)