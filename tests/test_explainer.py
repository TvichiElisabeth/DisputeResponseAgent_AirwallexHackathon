"""The facts the explainer hands the model. No model calls here."""
import os
from datetime import datetime, timezone

# The explainer imports core.config, which needs these to exist (values unused here).
os.environ.setdefault("AWX_CLIENT_ID", "test")
os.environ.setdefault("AWX_API_KEY", "test")

from merchant.explainer import _rejection_line  # noqa: E402
from merchant.policy import Dispute, EvidenceFlags, decide  # noqa: E402

NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
DUE = "2026-10-28T10:50:09+0000"
A_FLAGS = EvidenceFlags(prior_undisputed_matches=3, signed_delivery=True, delivery_scanned=True)


def test_after_rejection_the_model_is_told_how_the_bar_moved():
    rejected = Dispute("A", 1240.0, "USD", "FRAUDULENT", "CHARGEBACK",
                       "REQUIRES_RESPONSE", DUE, rejected_before=True)
    line = _rejection_line(decide(rejected, A_FLAGS, NOW))
    assert "2%" in line and "40%" in line and "$500" in line


def test_before_rejection_there_is_no_such_line():
    first = Dispute("A", 1240.0, "USD", "FRAUDULENT", "RFI", "REQUIRES_RESPONSE", DUE)
    assert _rejection_line(decide(first, A_FLAGS, NOW)) == ""
