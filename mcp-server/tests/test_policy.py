"""Deterministic policy-engine tests — part of the CI merge gate (no model needed)."""
from datetime import datetime, timedelta, timezone

from airlock_mcp.policy import evaluate_refund

POLICY = {"version": 3, "refund_window_days": 60, "max_auto_refund_cents": 20000}


def _order(status, days_old, amount):
    return {"status": status,
            "ordered_at": datetime.now(timezone.utc) - timedelta(days=days_old),
            "amount_cents": amount}


def test_approve_in_window_under_cap():
    assert evaluate_refund(_order("completed", 3, 6500), POLICY)["recommendation"] == "approve"


def test_escalate_over_cap():
    assert evaluate_refund(_order("completed", 5, 89000), POLICY)["recommendation"] == "escalate"


def test_refuse_outside_window():
    assert evaluate_refund(_order("completed", 75, 1500), POLICY)["recommendation"] == "refuse"


def test_refuse_already_refunded():
    assert evaluate_refund(_order("refunded", 10, 2500), POLICY)["recommendation"] == "refuse"
