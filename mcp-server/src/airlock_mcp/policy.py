"""Deterministic refund policy engine.

The decision (approve / refuse / escalate) is made HERE, in code, against a specific
policy version — and it returns the *reasoning* (each check, pass/fail) so the UI can
show exactly WHY, not just a verdict.
"""
from datetime import datetime, timezone


def _d(cents) -> str:
    return f"${cents / 100:,.2f}" if isinstance(cents, (int, float)) else "-"


def evaluate_refund(order: dict, policy: dict) -> dict:
    version = policy["version"]
    amount = order["amount_cents"]
    window = policy["refund_window_days"]
    cap = policy["max_auto_refund_cents"]
    status = order["status"]

    ordered_at = order["ordered_at"]
    if isinstance(ordered_at, str):
        ordered_at = datetime.fromisoformat(ordered_at)
    age_days = (datetime.now(timezone.utc) - ordered_at).days

    status_ok = status not in ("refunded", "cancelled")
    window_ok = age_days <= window
    under_cap = amount <= cap

    checks = [
        {"label": "Order eligible", "detail": status, "ok": status_ok},
        {"label": "Within refund window", "detail": f"{age_days} of {window} days", "ok": window_ok},
        {"label": "Under auto-refund cap", "detail": f"{_d(amount)} vs {_d(cap)} cap", "ok": under_cap},
    ]

    if not status_ok:
        rec, reason = "refuse", (f"Order has already been refunded." if status == "refunded"
                                 else "Order was cancelled; nothing to refund.")
    elif not window_ok:
        rec, reason = "refuse", f"Outside the {window}-day refund window (order is {age_days} days old)."
    elif not under_cap:
        rec, reason = "escalate", f"Amount {_d(amount)} exceeds the auto-refund cap ({_d(cap)}); needs human review."
    else:
        rec, reason = "approve", "Within policy window and under the auto-refund cap."

    return {
        "policy_version": version, "recommendation": rec, "reason": reason,
        "refundable_amount_cents": amount if rec in ("approve", "escalate") else 0,
        "window_days": window, "cap_cents": cap, "age_days": age_days,
        "amount_cents": amount, "checks": checks,
    }
