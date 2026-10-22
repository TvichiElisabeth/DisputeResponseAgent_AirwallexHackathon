"""Where a person comes in.

- request_approval(): the agent proposes an action, a person signs off (y/n).
  The approval is bound to a hash of everything shown: amount, currency,
  counterparty, order, product, reason code, action, evidence file.
- verify_approval(): called right before acting. If anything shown has changed
  since the person approved, the approval is void and the agent must not act.
- escalate(): the agent does NOT pick an action; it hands the case to a person
  with the facts and a checklist, and parks it in a human queue.
"""
import hashlib
import json
from datetime import datetime, timezone

from merchant.policy import Decision
from records import state as st
from records.evidence_text import ORDERS


def _terms(dispute: dict, decision: Decision, action_detail: str,
           evidence: dict | None) -> dict:
    """Everything the approver sees. Any change here voids the approval."""
    order = ORDERS[dispute["case"]]
    return {
        "case": dispute["case"],
        "dispute_id": dispute["id"],
        "stage": dispute["stage"],
        "action": decision.action,
        "action_detail": action_detail,            # e.g. PURCHASE_HISTORY
        "amount": float(dispute["amount"]),
        "currency": dispute["currency"],
        "counterparty": order["customer"],
        "order_id": order["order_id"],
        "product": order["product"],
        "reason_code": dispute["reason_code"],
        "evidence_file": evidence["filename"] if evidence else None,
        "evidence_sha256": evidence["sha256"] if evidence else None,
    }


def _hash(terms: dict) -> str:
    return hashlib.sha256(json.dumps(terms, sort_keys=True).encode()).hexdigest()


def _key(dispute: dict, decision: Decision) -> str:
    return f"{dispute['case']}_{dispute['id']}_{dispute['stage']}_{decision.action}"


def request_approval(state: dict, dispute: dict, decision: Decision, action_detail: str,
                     evidence: dict | None = None, explanation: str = "",
                     approver: str = "finance-ops-lead", ask=input, save=st.save) -> bool:
    terms = _terms(dispute, decision, action_detail, evidence)
    terms_hash = _hash(terms)
    approvals = state.setdefault("approvals", {})
    existing = approvals.get(_key(dispute, decision))

    if existing and existing["terms_sha256"] == terms_hash:
        return existing["approved"]               # same terms, already answered
    if existing:
        print("  ! Terms changed since the last approval. Asking again.")

    print("\n  ┌─ APPROVAL NEEDED " + "─" * 44)
    print(f"  │ Case {terms['case']}  {terms['dispute_id']}  ({terms['stage']})")
    print(f"  │ Action:       {terms['action']}  ({terms['action_detail']})")
    print(f"  │ Amount:       {terms['currency']} {terms['amount']:,.2f}")
    print(f"  │ Counterparty: {terms['counterparty']}")
    print(f"  │ Order:        {terms['order_id']}, {terms['product']}")
    print(f"  │ Reason code:  Visa {terms['reason_code']}")
    if evidence:
        print(f"  │ Evidence:     {terms['evidence_file']}  sha256 {terms['evidence_sha256'][:12]}…")
    print(f"  │ Why:          {decision.rule}")
    if explanation:
        print(f"  │ Note:         {explanation}")
    print("  └" + "─" * 62)

    approved = ask("  Approve? [y/n] ").strip().lower() == "y"
    approvals[_key(dispute, decision)] = {
        "approved": approved,
        "approved_by": approver if approved else None,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "terms": terms,
        "terms_sha256": terms_hash,
    }
    save(state)
    print(f"  -> {'APPROVED' if approved else 'REJECTED'} by {approver}\n")
    return approved


def verify_approval(state: dict, dispute: dict, decision: Decision, action_detail: str,
                    evidence: dict | None = None) -> str:
    """Call right before acting. Returns who approved, or raises PermissionError."""
    record = state.get("approvals", {}).get(_key(dispute, decision))
    if not record or not record["approved"]:
        raise PermissionError(f"[{dispute['case']}] no approval on record; not acting.")
    if record["terms_sha256"] != _hash(_terms(dispute, decision, action_detail, evidence)):
        raise PermissionError(f"[{dispute['case']}] terms changed after approval; not acting.")
    return record["approved_by"]


def escalate(state: dict, dispute: dict, decision: Decision, explanation: str,
             what_to_check: list[str], save=st.save) -> dict:
    queue = state.setdefault("human_queue", {})
    if dispute["case"] in queue:
        return queue[dispute["case"]]

    order = ORDERS[dispute["case"]]
    item = {
        "dispute_id": dispute["id"],
        "amount": float(dispute["amount"]),
        "currency": dispute["currency"],
        "counterparty": order["customer"],
        "order_id": order["order_id"],
        "due_at": dispute["due_at"],
        "reason": decision.rule,
        "explanation": explanation,
        "what_to_check": what_to_check,
        "status": "WAITING_FOR_PERSON",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    queue[dispute["case"]] = item
    save(state)

    print("\n  ┌─ ESCALATED TO A PERSON " + "─" * 38)
    print(f"  │ Case {dispute['case']}  {dispute['id']}  due {dispute['due_at']}")
    print(f"  │ {item['currency']} {item['amount']:,.2f}, {order['customer']}, "
          f"{order['order_id']} ({order['product']})")
    print(f"  │ Why:  {decision.rule}")
    if explanation:
        print(f"  │ Note: {explanation}")
    for check in what_to_check:
        print(f"  │  - check: {check}")
    print("  └" + "─" * 62 + "\n")
    return item