"""Raw PII must never reach trace/log storage. This locks the redactor."""
from airlock_mcp.redaction import redact


def test_masks_email_field():
    out = redact({"customer_id": "CUST-01", "email": "ava@example.com"})
    assert out["email"] == "***REDACTED***"
    assert out["customer_id"] == "CUST-01"


def test_masks_email_anywhere_in_strings():
    out = redact({"note": "contact ava@example.com re: refund"})
    assert "ava@example.com" not in out["note"]


def test_masks_nested_and_lists():
    out = redact({"items": [{"email": "x@y.com"}, {"phone": "12345"}]})
    assert out["items"][0]["email"] == "***REDACTED***"
    assert out["items"][1]["phone"] == "***REDACTED***"
