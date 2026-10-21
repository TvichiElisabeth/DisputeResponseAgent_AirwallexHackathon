"""Record payments made through payment links into records/state.json.

Matches each case to the newest SUCCEEDED payment intent with the same
amount and currency. Run once after paying the links.
"""
from core.client import AirwallexClient
from records import state as st
from records.cases import CASES


def record_payments(client: AirwallexClient, state: dict) -> None:
    res = client.get("/pa/payment_intents", params={"page_size": 100})
    paid = [pi for pi in res.get("items", []) if pi.get("status") == "SUCCEEDED"]
    paid.sort(key=lambda pi: pi.get("created_at", ""), reverse=True)  # newest first

    used = set()
    for case in CASES:
        match = next((pi for pi in paid
                      if pi["id"] not in used
                      and float(pi["amount"]) == case.amount
                      and pi["currency"] == case.currency), None)
        if not match:
            raise RuntimeError(f"No SUCCEEDED {case.currency} {case.amount} payment for case {case.key}")
        used.add(match["id"])

        old = state.setdefault("payments", {}).get(case.key)
        if old and old.get("id") != match["id"]:
            state.setdefault("abandoned_payments", []).append(old)

        state["payments"][case.key] = {
            "id": match["id"],
            "amount": case.amount,
            "currency": case.currency,
            "status": "SUCCEEDED",
            "source": "payment_link",
        }
        print(f"[{case.key}] recorded {match['id']}  {case.currency} {case.amount:,.2f}")

    st.save(state)


if __name__ == "__main__":
    record_payments(AirwallexClient(), st.load())