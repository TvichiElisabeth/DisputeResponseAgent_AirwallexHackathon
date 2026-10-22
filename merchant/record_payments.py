"""Record payments made through payment links into records/state.json.

Matches each case to the newest SUCCEEDED payment intent with the same amount
and currency that has NOT been used before: not in an earlier run's archive,
and without a dispute already open on it in Airwallex.
"""
from core.client import AirwallexClient
from records import state as st
from records.cases import CASES


def disputed_payment_ids(client: AirwallexClient) -> set[str]:
    res = client.get("/pa/payment_disputes", params={"page_size": 100})
    return {d["payment_intent_id"] for d in res.get("items", []) if d.get("payment_intent_id")}


def record_payments(client: AirwallexClient, state: dict) -> None:
    res = client.get("/pa/payment_intents", params={"page_size": 100})
    paid = [pi for pi in res.get("items", []) if pi.get("status") == "SUCCEEDED"]
    paid.sort(key=lambda pi: pi.get("created_at", ""), reverse=True)  # newest first

    taken = st.used_payment_ids() | disputed_payment_ids(client)

    for case in CASES:
        current = state.setdefault("payments", {}).get(case.key)
        if current:
            print(f"[{case.key}] already recorded {current['id']}, keeping it")
            taken.add(current["id"])
            continue

        match = next((pi for pi in paid
                      if pi["id"] not in taken
                      and float(pi["amount"]) == case.amount
                      and pi["currency"] == case.currency), None)
        if not match:
            raise SystemExit(f"[{case.key}] no unused SUCCEEDED {case.currency} "
                             f"{case.amount:,.2f} payment. Pay a new payment link first.")
        taken.add(match["id"])

        state["payments"][case.key] = {
            "id": match["id"],
            "amount": case.amount,
            "currency": case.currency,
            "status": "SUCCEEDED",
            "source": "payment_link",
        }
        st.save(state)
        print(f"[{case.key}] recorded {match['id']}  {case.currency} {case.amount:,.2f}")


if __name__ == "__main__":
    record_payments(AirwallexClient(), st.load())