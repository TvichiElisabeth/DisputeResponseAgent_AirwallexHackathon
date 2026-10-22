"""Airwallex-inspired web view for the dispute agent.

Run: streamlit run app.py

Same agent, same rules, same approvals as the terminal.
Only the presentation has changed.
"""
import contextlib
import io

import streamlit as st

from bank.reject import reject_evidence
from bank.sandbox import AirwallexSandboxSimulator
from bank.seed import open_disputes
from core.client import AirwallexClient
from merchant import agent, refunds
from merchant.policy import DISPUTE_FEE, ESCALATE, CHALLENGE
from merchant.queue import read_queue
from merchant.record_payments import record_payments
from records import state as store
from records.evidence_text import ORDERS


NEW_INFO = (
    "The issuing bank rejected our evidence and moved the case to CHARGEBACK."
)

COLOR = {
    "ACCEPT": "green",
    "CHALLENGE": "blue",
    "ESCALATE": "orange",
}


st.set_page_config(
    page_title="Dispute Response Agent | Airwallex Hackathon",
    page_icon="⚖️",
    layout="wide",
)

# ---------------- Airwallex-inspired styling ----------------

st.markdown(
    """
    <style>
        :root {
            --aw-blue: #2563EB;
            --aw-blue-hover: #1D4ED8;
            --aw-ink: #172B4D;
            --aw-muted: #64748B;
            --aw-border: #E2E8F0;
            --aw-surface: #FFFFFF;
            --aw-page: #F7F9FC;
        }

        .stApp {
            background: var(--aw-page);
            color: var(--aw-ink);
            font-family: Inter, -apple-system, BlinkMacSystemFont,
                         "Segoe UI", sans-serif;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stAppViewContainer"] > .main {
            background: var(--aw-page);
        }

        [data-testid="stMainBlockContainer"] {
            max-width: 1440px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        /* Sidebar */

        [data-testid="stSidebar"] {
            background: #FFFFFF;
            border-right: 1px solid var(--aw-border);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.5rem;
        }

        [data-testid="stSidebar"] h2 {
            color: var(--aw-ink);
            font-size: 0.95rem;
            font-weight: 650;
            letter-spacing: -0.01em;
        }

        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: var(--aw-muted);
            font-size: 0.78rem;
            line-height: 1.6;
        }

        /* Typography */

        h1 {
            color: var(--aw-ink) !important;
            font-size: 1.85rem !important;
            font-weight: 650 !important;
            letter-spacing: -0.045em !important;
            line-height: 1.25 !important;
        }

        h2, h3, h4 {
            color: var(--aw-ink) !important;
            letter-spacing: -0.025em;
            font-weight: 620 !important;
        }

        h2 {
            font-size: 1.2rem !important;
        }

        h3 {
            font-size: 1.05rem !important;
        }

        h4 {
            font-size: 0.98rem !important;
        }

        [data-testid="stCaptionContainer"] {
            color: var(--aw-muted);
            font-size: 0.82rem;
        }

        /* Metric cards */

        [data-testid="stMetric"] {
            background: var(--aw-surface);
            border: 1px solid var(--aw-border);
            border-radius: 10px;
            padding: 18px 20px;
            min-height: 105px;
            box-shadow: none;
        }

        [data-testid="stMetricLabel"] {
            color: var(--aw-muted);
            font-size: 0.82rem;
            font-weight: 500;
        }

        [data-testid="stMetricValue"] {
            color: var(--aw-ink);
            font-size: 1.65rem;
            font-weight: 650;
            letter-spacing: -0.04em;
        }

        [data-testid="stMetricDelta"] {
            font-size: 0.78rem;
        }

        /* Tables */

        [data-testid="stDataFrame"] {
            background: #FFFFFF;
            border: 1px solid var(--aw-border);
            border-radius: 10px;
            overflow: hidden;
        }

        [data-testid="stDataFrame"] iframe {
            border-radius: 10px;
        }

        /* Buttons */

        .stButton > button {
            border-radius: 7px;
            border: 1px solid #D5DEEA;
            background: #FFFFFF;
            color: var(--aw-ink);
            font-size: 0.86rem;
            font-weight: 550;
            min-height: 38px;
            padding: 0.45rem 1rem;
            transition: background 120ms ease,
                        border-color 120ms ease;
        }

        .stButton > button:hover {
            border-color: var(--aw-blue);
            color: var(--aw-blue);
            background: #F5F8FF;
        }

        .stButton > button:focus-visible {
            outline: 2px solid var(--aw-blue);
            outline-offset: 2px;
            box-shadow: none;
        }

        .stButton > button[kind="primary"] {
            background: var(--aw-blue);
            color: #FFFFFF;
            border-color: var(--aw-blue);
            font-weight: 600;
        }

        .stButton > button[kind="primary"]:hover {
            background: var(--aw-blue-hover);
            border-color: var(--aw-blue-hover);
            color: #FFFFFF;
        }

        /* Containers and dispute cards */

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF;
            border: 1px solid var(--aw-border) !important;
            border-radius: 10px !important;
            box-shadow: none !important;
        }

        /* Activity log */

        [data-testid="stSidebar"] [data-testid="stCodeBlock"] {
            border: 1px solid var(--aw-border);
            border-radius: 7px;
            background: #F8FAFC;
        }

        [data-testid="stCodeBlock"] pre {
            font-size: 0.74rem;
            line-height: 1.55;
        }

        /* Dividers and alerts */

        hr {
            border-color: var(--aw-border) !important;
            margin-top: 1rem;
            margin-bottom: 1rem;
        }

        [data-testid="stAlert"] {
            border-radius: 8px;
        }

        /* Responsive layout */

        @media (max-width: 768px) {
            [data-testid="stMainBlockContainer"] {
                padding: 1rem 1rem 2rem;
            }

            h1 {
                font-size: 1.5rem !important;
            }

            [data-testid="stMetric"] {
                padding: 12px;
            }

            [data-testid="stMetricValue"] {
                font-size: 1.3rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------- Session state ----------------

for key, value in {
    "plan": None,
    "log": [],
    "outcome": {},
}.items():
    st.session_state.setdefault(key, value)


# ---------------- Shared client and helpers ----------------

@st.cache_resource
def get_client() -> AirwallexClient:
    return AirwallexClient()


def capture(fn, *args, **kwargs):
    """Run a function and capture its printed output for the activity log."""
    buf = io.StringIO()

    with contextlib.redirect_stdout(buf):
        result = fn(*args, **kwargs)

    if text := buf.getvalue().strip():
        st.session_state.log.append(text)

    return result

def md(text: str) -> str:
    """Show $ amounts literally; Streamlit would otherwise read $...$ as maths."""
    return text.replace("$", r"\$")

def item_key(it: dict) -> str:
    return (
        f"{it['decision'].case}-"
        f"{it['row']['id']}-"
        f"{it['row']['stage']}-"
        f"{it['decision'].action}"
    )


client = get_client()


# ---------------- Sidebar: sandbox controls and activity ----------------

with st.sidebar:
    st.markdown("## Sandbox controls")
    st.caption(
        "Initialize test payments and open sandbox disputes."
    )

    if st.button(
        "Record payments + open disputes",
        use_container_width=True,
    ):
        try:
            capture(record_payments, client, store.load())
            capture(
                open_disputes,
                AirwallexSandboxSimulator(client),
                store.load(),
            )
            st.session_state.plan = None
        except SystemExit as e:
            st.error(str(e))

    st.divider()

    st.markdown("## Issuer simulation")
    st.caption(
        "Simulate the issuing bank rejecting Case A's evidence."
    )

    if st.button(
        "Reject Case A evidence",
        use_container_width=True,
    ):
        try:
            capture(
                reject_evidence,
                client,
                store.load(),
                "A",
            )
            st.session_state.plan = None
        except SystemExit as e:
            st.warning(str(e))

    st.divider()

    st.markdown("## Recent activity")

    if not st.session_state.log:
        st.caption("Activity will appear here.")
    else:
        for entry in reversed(st.session_state.log[-8:]):
            st.code(entry, language=None)


# ---------------- Header and queue data ----------------

st.title("Dispute Response Agent")
st.caption("Built on the Airwallex sandbox · review chargebacks, approve responses, track outcomes.")

st.divider()

state = store.load()

try:
    rows = read_queue(client, state)
except KeyError:
    st.info(
        "No disputes found. Initialize the sandbox using the controls "
        "in the sidebar."
    )
    st.stop()


actions_log = state.get("actions", {})
waiting = state.get("human_queue", {})

open_rows = [
    row
    for row in rows
    if row["status"] == "REQUIRES_RESPONSE"
    and row["case"] not in waiting
]

fees = sum(
    DISPUTE_FEE
    for row in rows
    if any(
        op.startswith(f"challenge_{row['case']}_{row['id']}_")
        for op in actions_log
    )
)


# ---------------- Summary metrics ----------------

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "Open disputes",
    len(open_rows),
)

m2.metric(
    "Money at stake",
    f"${sum(float(row['amount']) for row in open_rows):,.2f}",
)

m3.metric(
    "Escalated to a person",
    len(waiting),
)

m4.metric(
    "Dispute fees paid",
    f"${fees:,.2f}",
)


# ---------------- Dispute queue ----------------

st.subheader("Dispute queue")

st.dataframe(
    [
        {
            "Case": row["case"],
            "Amount": (
                f"{row['currency']} {float(row['amount']):,.2f}"
            ),
            "Visa code": row["reason_code"],
            "Claim": row["reason_type"],
            "Stage": row["stage"],
            "Status": row["status"],
            "Due": row["due_at"][:10],
        }
        for row in rows
    ],
    hide_index=True,
    use_container_width=True,
)


# ---------------- Agent recommendations ----------------

st.subheader("Recommended actions")

st.caption(
    "Review the proposed response for each dispute. "
    "Actions requiring approval remain subject to human sign-off."
)

if st.button(
    "Review open disputes",
    type="primary",
):
    with st.spinner("Reviewing dispute evidence and deadlines..."):
        items = capture(
            agent.plan,
            client,
            store.load(),
            NEW_INFO,
        )

        for item in items:
            decision = item["decision"]
            # Fresh review, fresh answer: forget an earlier Reject on this card.
            st.session_state.outcome.pop(item_key(item), None)

            if (
                decision.action == ESCALATE
                or not decision.needs_human
            ):
                capture(
                    agent.act,
                    client,
                    store.load(),
                    item,
                    lambda _: "y",
                )

                st.session_state.outcome[item_key(item)] = (
                    "Escalated to a person"
                    if decision.action == ESCALATE
                    else "Completed automatically"
                )

            elif decision.action == CHALLENGE:
                capture(
                    agent.evidence_for,
                    client,
                    store.load(),
                    item["row"],
                    item["flags"],
                )

        st.session_state.plan = items

    st.rerun()


# ---------------- Individual decision cards ----------------

for item in st.session_state.plan or []:
    decision = item["decision"]
    row = item["row"]
    note = item["note"]
    key = item_key(item)

    with st.container(border=True):
        left, right = st.columns([3, 1])

        badge = (
            f":{COLOR[decision.action]}[**{decision.action}**]"
        )

        if decision.urgent:
            badge += " · :red[**URGENT**]"

        left.markdown(
            f"#### Case {decision.case} · "
            f"{row['currency']} {float(row['amount']):,.2f} · "
            f"{badge}"
        )

        left.caption(
            f"Visa {row['reason_code']} · "
            f"{row['reason_type']} · "
            f"{row['stage']} · "
            f"{decision.days_left} days remaining · "
            f"Win chance {decision.p_win:.0%}"
        )

        left.markdown(md(note["explanation"]))

        if note["what_to_check"]:
            left.markdown(
                "**Evidence to verify**\n"
                + "\n".join(
                    f"- {md(check)}"
                    for check in note["what_to_check"]
                )
            )

        right.metric(
            "Cost to accept",
            f"${decision.cost_if_accept:,.2f}",
        )

        right.metric(
            "Expected challenge cost",
            f"${decision.expected_cost_if_challenge:,.2f}",
        )

        if key in st.session_state.outcome:
            st.success(
                st.session_state.outcome[key]
            )

        elif decision.needs_human:
            order = ORDERS[decision.case]

            evidence = (
                store.load()
                .get("evidence_files", {})
                .get(decision.case)
                if decision.action == CHALLENGE
                else None
            )

            approval_text = (
                f"**Approval required:** {decision.action} · "
                f"{row['currency']} {float(row['amount']):,.2f} · "
                f"{order['customer']} · "
                f"{order['order_id']} ({order['product']}) · "
                f"Visa {row['reason_code']}"
            )

            if evidence:
                approval_text += (
                    f" · Evidence `{evidence['filename']}` "
                    f"· SHA-256 `{evidence['sha256'][:12]}…`"
                )

            st.markdown(approval_text)

            approve_col, reject_col, _ = st.columns([1, 1, 4])

            if approve_col.button(
                "Approve",
                key=f"ok-{key}",
                type="primary",
            ):
                try:
                    capture(
                        agent.act,
                        client,
                        store.load(),
                        item,
                        lambda _: "y",
                    )
                    st.session_state.outcome[key] = (
                        "Approved and completed"
                    )
                except Exception as e:  # show the reason, keep the page usable
                    st.session_state.outcome[key] = (
                        f"Not completed: {e}"
                    )

                st.rerun()

            if reject_col.button(
                "Reject",
                key=f"no-{key}",
            ):
                try:
                    capture(
                        agent.act,
                        client,
                        store.load(),
                        item,
                        lambda _: "n",
                    )
                    st.session_state.outcome[key] = (
                        "Not approved — no action taken"
                    )
                except Exception as e:
                    st.session_state.outcome[key] = (
                        f"Not completed: {e}"
                    )

                st.rerun()


# ---------------- Cases requiring human attention ----------------

if waiting:
    st.subheader("Requires attention")

    st.caption(
        "These cases are waiting for additional information or "
        "human review."
    )

    for case, item in waiting.items():
        with st.container(border=True):
            st.markdown(
                f"#### Case {case} · "
                f"{item['currency']} {item['amount']:,.2f}"
            )

            st.caption(
                f"{item['counterparty']} · "
                f"Order {item['order_id']} · "
                f"Due {item['due_at'][:10]}"
            )

            st.markdown(md(item["explanation"]))

            for check in item["what_to_check"]:
                st.markdown(f"- {md(check)}")


# ---------------- Dispute outcomes ----------------

st.subheader("Dispute outcomes")

summary = []
refunded = 0.0
conceded = 0.0

for row in rows:
    challenged = any(
        op.startswith(
            f"challenge_{row['case']}_{row['id']}_"
        )
        for op in actions_log
    )

    back = refunds.refunded_amount(
        client,
        state["payments"][row["case"]]["id"],
    )

    if row["case"] in waiting:
        outcome = "Waiting for review"

    elif back:
        outcome = f"Refunded ${back:,.2f}"
        refunded += back

    elif row["status"] == "ACCEPTED":
        outcome = "Conceded"
        conceded += float(row["amount"])

    else:
        outcome = "Open"

    summary.append(
        {
            "Case": row["case"],
            "Amount": (
                f"{row['currency']} {float(row['amount']):,.2f}"
            ),
            "Final status": (
                f"{row['stage']} / {row['status']}"
            ),
            "Fee paid": (
                f"${DISPUTE_FEE if challenged else 0:,.2f}"
            ),
            "Outcome": outcome,
        }
    )

st.dataframe(
    summary,
    hide_index=True,
    use_container_width=True,
)


# ---------------- Financial totals ----------------

r1, r2, r3 = st.columns(3)

r1.metric(
    "Refunded to customers",
    f"${refunded:,.2f}",
)

r2.metric(
    "Conceded",
    f"${conceded:,.2f}",
)

r3.metric(
    "Dispute fees paid",
    f"${fees:,.2f}",
)