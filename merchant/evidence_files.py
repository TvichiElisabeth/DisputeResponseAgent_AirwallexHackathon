"""Build the evidence PDF for a challenged case and upload it to Airwallex.

Only cases we CHALLENGE get a file. PDF only: Airwallex rejects PNG.
"""
import hashlib
from pathlib import Path

from fpdf import FPDF

from core.client import AirwallexClient
from records import state as st
from records.evidence_text import EVIDENCE

EVIDENCE_DIR = Path(__file__).resolve().parent.parent / "records" / "evidence"


def build_pdf(case_key: str, dispute: dict, summary: str) -> Path:
    """dispute: a row from merchant.queue.read_queue(). summary: the argument."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Dispute response - compelling evidence", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    for label, value in [
        ("Dispute ID", dispute["id"]),
        ("Amount", f"{dispute['currency']} {float(dispute['amount']):,.2f}"),
        ("Reason", f"Visa {dispute['reason_code']} ({dispute['reason_type']})"),
    ]:
        pdf.cell(0, 7, f"{label}: {value}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, summary)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Supporting records", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", "", 8)
    pdf.multi_cell(0, 4, EVIDENCE[case_key])

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE_DIR / f"{case_key}_compelling_evidence.pdf"  # < 50 chars
    pdf.output(str(path))
    return path


def upload(client: AirwallexClient, state: dict, case_key: str, path: Path) -> dict:
    """Upload once per file version. Returns {"file_id", "sha256"}."""
    content = path.read_bytes()
    sha = hashlib.sha256(content).hexdigest()

    files_state = state.setdefault("evidence_files", {})
    existing = files_state.get(case_key)
    if existing and existing["sha256"] == sha:
        print(f"[{case_key}] same file already uploaded ({existing['file_id']}), skipping")
        return existing

    res = client.post(
        "/files/upload",
        files={"file": (path.name, content, "application/pdf")},
        data={"notes": f"Dispute evidence case {case_key}"},   # max 50 chars
        use_files_host=True,
    )
    record = {"file_id": res["file_id"], "sha256": sha, "filename": path.name}
    files_state[case_key] = record
    st.save(state)
    print(f"[{case_key}] uploaded {path.name} -> {record['file_id']}")
    return record


if __name__ == "__main__":
    from merchant.queue import read_queue

    client = AirwallexClient()
    state = st.load()
    row = next(r for r in read_queue(client, state) if r["case"] == "A")

    summary = (
        "The cardholder made this purchase. The device fingerprint (fp_8c21e9) and "
        "IP address (82.77.14.203) match three earlier orders from the same customer, "
        "none of which were disputed. The order was delivered and signed for by "
        "J. MARIN, the cardholder's name."
    )
    path = build_pdf("A", row, summary)
    print("Built", path)
    upload(client, state, "A", path)