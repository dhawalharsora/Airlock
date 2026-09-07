"""PII redaction — applied at the tool boundary before anything is logged or traced.

Redaction happens in ONE place (here) and is called by the logging middleware and
by every audit/trace write, so observability can never become a data leak.
"""
import re

# Field names whose values are masked wholesale, wherever they appear.
PII_FIELDS = {"email", "customer_email", "phone", "phone_number"}

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_MASK = "***REDACTED***"


def _mask_emails(text: str) -> str:
    return _EMAIL_RE.sub(_MASK, text)


def redact(obj):
    """Return a deep copy of obj with PII masked. Handles dicts, lists, strings."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k.lower() in PII_FIELDS:
                out[k] = _MASK
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [redact(v) for v in obj]
    if isinstance(obj, str):
        return _mask_emails(obj)
    return obj
