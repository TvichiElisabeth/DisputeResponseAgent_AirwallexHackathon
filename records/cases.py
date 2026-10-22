"""The demo's chargeback queue: one definition per case (synthetic data).

Evidence text is added in chunk 5. Change amounts and deadlines here only.
"""
from dataclasses import dataclass

#Intructions:  Use Visa reason codes 10.4, 13.1 or 13.6.
#Visa Reason Codes Meaning
#10.4: (Other Fraud / Card-Absent Environment) The cardholder claims they did not authorize or participate in an online, phone, or mail-order transaction.
#13.1:  (Merchandise/Services Not Received)
#13.6:  Credit Not Processed) The cardholder claims that they are owed a refund or credit that the merchant has failed to issue.

@dataclass(frozen=True)
class Case:
    key: str            # "A", "B", "C"
    title: str
    amount: float       # major units: 18.0 = $18.00
    currency: str
    reason_code: str    # Visa reason code
    start_stage: str    # where the bank opens the dispute
    due_days: int       # deadline, days from now
    order_ref: str      # prefix for merchant_order_id


CASES = [
    Case("A", "Fraud claim, strong evidence", 1240.00, "USD", "10.4", "RFI", 7, "ORD-A"),
    Case("B", "Not received, small amount",     18.00, "USD", "13.1", "RFI", 5, "ORD-B"),
    Case("C", "Credit not processed",          340.00, "USD", "13.6", "CHARGEBACK", 10, "ORD-C"),
]