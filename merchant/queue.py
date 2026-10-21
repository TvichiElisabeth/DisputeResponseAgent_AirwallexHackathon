"""Merchant side: read the chargeback queue the way the agent sees it."""
from core.client import AirwallexClient
from records import state as st
from records.cases import CASES


def read_queue(client: AirwallexClient, state: dict) -> list[dict]:
    res = client.get("/pa/payment_disputes", params={"page_size": 100})
    by_id = {d["id"]: d for d in res.get("items", [])}

    queue = []
    for case in CASES:
        dispute_id = state["disputes"][case.key]["id"]
        d = by_id.get(dispute_id) or client.get(f"/pa/payment_disputes/{dispute_id}")
        reason = d.get("reason") or {}
        row = {
            "case": case.key,
            "id": d["id"],
            "amount": d.get("amount"),
            "currency": d.get("currency"),
            "reason_code": reason.get("original_code"),
            "reason_type": reason.get("type"),
            "stage": d.get("stage"),
            "status": d.get("status"),
            "due_at": d.get("due_at"),
        }
        state["disputes"][case.key].update({k: row[k] for k in ("stage", "status", "due_at")})
        queue.append(row)
    st.save(state)
    return queue


if __name__ == "__main__":
    print("Chargeback queue:")
    for r in read_queue(AirwallexClient(), st.load()):
        print(f"  {r['case']}  {r['id']}  {r['currency']} {r['amount']:>9}  "
              f"{r['reason_code'] or '-':<5} {r['reason_type'] or '-':<22} "
              f"{r['stage']:<11} {r['status']:<18} due {r['due_at']}")