"""Airlock MCP tool server — the governed boundary.

Read tools return data. High-risk tools (issue_refund / issue_replacement) are
GATED: they can only queue a pending approval, never execute. Policy is evaluated
deterministically in code, and the gate re-validates policy itself (defense in
depth) so a misbehaving agent still cannot push through an ineligible refund.
"""
from dotenv import load_dotenv
from fastmcp import FastMCP

from airlock_mcp.db import (
    fetch_one,
    get_active_policy,
    queue_approval,
    write_audit,
)
from airlock_mcp.middleware.pii_logging import PIIRedactionMiddleware
from airlock_mcp.policy import evaluate_refund

load_dotenv()

mcp = FastMCP("airlock-tools")
mcp.add_middleware(PIIRedactionMiddleware())  # redacted logging for every tool call

AGENT = "agent"


# ---------- read tools (low risk) ----------

@mcp.tool
def get_order(order_id: str) -> dict:
    """Look up a single order by ID (e.g. 'ORD-1001'). Read-only."""
    row = fetch_one(
        """
        SELECT o.order_id, o.item, o.amount_cents, o.currency, o.status,
               o.ordered_at, c.customer_id, c.name AS customer_name, c.email
        FROM orders o JOIN customers c ON c.customer_id = o.customer_id
        WHERE o.order_id = %s
        """,
        (order_id,),
    )
    if row is None:
        return {"found": False, "order_id": order_id}
    row["found"] = True
    row["ordered_at"] = row["ordered_at"].isoformat()
    return row


@mcp.tool
def get_customer(customer_id: str) -> dict:
    """Look up a customer by ID. Returns contact details (PII); read-only."""
    row = fetch_one(
        "SELECT customer_id, name, email FROM customers WHERE customer_id = %s",
        (customer_id,),
    )
    return row or {"found": False, "customer_id": customer_id}


@mcp.tool
def lookup_policy(order_id: str) -> dict:
    """Return the governed refund recommendation for an order against the ACTIVE
    policy version: approve | refuse | escalate, with the reason. Deterministic.
    Records the decision to the audit trail."""
    order = fetch_one("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    if order is None:
        return {"found": False, "order_id": order_id}
    policy = get_active_policy()
    ev = evaluate_refund(order, policy)
    write_audit(AGENT, "policy_decision", "order", order_id,
                {"amount_cents": order["amount_cents"]},
                ev["recommendation"], ev["policy_version"])
    ev["found"] = True
    return ev


# ---------- high-risk tools (GATED) ----------

def _gate_refund(order_id: str, amount_cents: int, action: str, rationale: str) -> dict:
    order = fetch_one("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    if order is None:
        return {"status": "error", "reason": f"Unknown order {order_id}"}
    policy = get_active_policy()
    ev = evaluate_refund(order, policy)

    # Defense in depth: the gate itself refuses to queue anything policy won't allow.
    if ev["recommendation"] != "approve":
        write_audit(AGENT, action, "order", order_id,
                    {"amount_cents": amount_cents}, f"blocked:{ev['recommendation']}",
                    ev["policy_version"])
        return {"status": "blocked", "reason": ev["reason"],
                "recommendation": ev["recommendation"]}

    if amount_cents > ev["refundable_amount_cents"]:
        write_audit(AGENT, action, "order", order_id,
                    {"amount_cents": amount_cents}, "blocked:amount_too_high",
                    ev["policy_version"])
        return {"status": "blocked",
                "reason": f"Requested ${amount_cents/100:,.2f} exceeds refundable "
                          f"${ev['refundable_amount_cents']/100:,.2f}."}

    approval_id = queue_approval(order_id, action, amount_cents, ev["policy_version"],
                                 ev["reason"], rationale)
    write_audit(AGENT, action, "approval", str(approval_id),
                {"amount_cents": amount_cents}, "pending_approval", ev["policy_version"])
    return {"status": "pending_approval", "approval_id": approval_id,
            "note": "Queued for human approval. The action has NOT executed."}


@mcp.tool
def issue_refund(order_id: str, amount_cents: int, rationale: str = "") -> dict:
    """HIGH-RISK. Does not move money. Queues a pending refund for human approval,
    only if policy allows it. Returns the pending approval id."""
    return _gate_refund(order_id, amount_cents, "issue_refund", rationale)


@mcp.tool
def issue_replacement(order_id: str, rationale: str = "") -> dict:
    """HIGH-RISK. Queues a pending replacement for human approval (same gate)."""
    order = fetch_one("SELECT amount_cents FROM orders WHERE order_id = %s", (order_id,))
    amt = order["amount_cents"] if order else 0
    return _gate_refund(order_id, amt, "issue_replacement", rationale)


@mcp.tool
def escalate(order_id: str, reason: str) -> dict:
    """Hand a decision to a human when policy says escalate or is ambiguous.
    Queues an escalation and audits it. No money moves."""
    policy = get_active_policy()
    order = fetch_one("SELECT amount_cents FROM orders WHERE order_id = %s", (order_id,))
    amount = order["amount_cents"] if order else 0
    approval_id = queue_approval(order_id, "escalate", amount, policy["version"],
                                 reason, reason)
    write_audit(AGENT, "escalate", "approval", str(approval_id),
                {}, "escalated", policy["version"])
    return {"status": "escalated", "approval_id": approval_id}


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8081)
