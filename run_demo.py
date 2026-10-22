"""The whole demo in one command.

Before running: python -m records.reset, then pay 3 new payment links
($1,240 / $18 / $340 USD) with the test card.

    python run_demo.py            # pauses between beats, you approve with y/n
    python run_demo.py --yes      # rehearsal: auto-approve, no pauses
"""
import argparse

from bank.reject import reject_evidence
from bank.sandbox import AirwallexSandboxSimulator
from bank.seed import open_disputes
from core.client import AirwallexClient, AirwallexError
from merchant import agent, refunds
from merchant.policy import DISPUTE_FEE
from merchant.queue import read_queue
from merchant.record_payments import record_payments
from records import state as st

NEW_INFO = "The issuing bank rejected our evidence and moved the case to CHARGEBACK."


def beat(n: int, title: str, pause: bool) -> None:
    print("\n" + "=" * 72)
    print(f"  {n}. {title}")
    print("=" * 72)
    if pause:
        input("  (press Enter) ")


def show_queue(client) -> None:
    for r in read_queue(client, st.load()):
        print(f"  {r['case']}  {r['currency']} {float(r['amount']):>8,.2f}  Visa {r['reason_code']:<5}"
              f"{r['reason_type']:<22}{r['stage']:<11}{r['status']:<18}due {r['due_at'][:10]}")


def money_summary(client) -> None:
    state = st.load()
    actions = state.get("actions", {})
    waiting = state.get("human_queue", {})
    fees = lost = refunded = pending = 0.0

    print(f"  {'case':<5}{'amount':>10}  {'final status':<20}{'fee paid':>9}  outcome")
    for r in read_queue(client, state):
        case, amount = r["case"], float(r["amount"])
        challenged = any(op.startswith(f"challenge_{case}_{r['id']}_") for op in actions)
        fee = DISPUTE_FEE if challenged else 0.0
        back = refunds.refunded_amount(client, state["payments"][case]["id"])

        if case in waiting:
            outcome, pending = "waiting on a person", pending + amount
        elif r["status"] in ("WON", "REVERSED"):
            outcome = "kept the money"
        elif back:
            outcome, refunded = f"refunded ${back:,.2f} to the customer", refunded + back
        elif r["status"] == "ACCEPTED":
            outcome, lost = "conceded after the bank's rejection", lost + amount
        else:
            outcome = r["status"]
        fees += fee
        print(f"  {case:<5}{r['currency']} {amount:>6,.2f}  {r['stage'] + ' / ' + r['status']:<20}"
              f"{fee:>9,.2f}  {outcome}")

    print(f"\n  Refunded to customers: ${refunded:,.2f}")
    print(f"  Conceded:              ${lost:,.2f}")
    print(f"  Dispute fees paid:     ${fees:,.2f}   (applied in code; the sandbox doesn't deduct them)")
    print(f"  Waiting on a person:   ${pending:,.2f}")

    try:   # resulting balance, if the key has Balances > Read
        usd = next((b for b in client.get("/balances/current") if b.get("currency") == "USD"), None)
        if usd:
            print(f"  USD available balance: ${float(usd['available_amount']):,.2f}")
    except (AirwallexError, TypeError, KeyError):
        pass


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--yes", action="store_true", help="auto-approve and skip pauses (rehearsal)")
    args = p.parse_args()
    pause = not args.yes
    ask = (lambda _: "y") if args.yes else input
    client = AirwallexClient()

    beat(0, "GOAL", False)
    print("  Finance ops lead at an online merchant: clear the chargeback queue before the")
    print(f"  deadlines without spending more on fees (${DISPUTE_FEE:.0f} per defended dispute) "
          "than we recover.")

    beat(1, "SETUP: three paid orders, and the bank opens three disputes", pause)
    record_payments(client, st.load())
    open_disputes(AirwallexSandboxSimulator(client), st.load())

    beat(2, "THE QUEUE (read from Airwallex)", pause)
    show_queue(client)

    beat(3, "THE AGENT'S PLAN, AND WHAT IT DOES", pause)
    agent.run(ask=ask)

    beat(4, "NEW INFORMATION: the issuing bank rejects our evidence on A", pause)
    reject_evidence(client, st.load(), "A")

    beat(5, "REVISED DECISION", pause)
    agent.run(NEW_INFO, ask=ask)

    beat(6, "RESULT", pause)
    money_summary(client)


if __name__ == "__main__":
    main()