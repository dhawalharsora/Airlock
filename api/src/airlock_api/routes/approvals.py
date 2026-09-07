"""Approval queue: list pending high-risk actions, approve (executes), reject."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from airlock_api.auth import require_approver
from airlock_api.db import execute_approval, fetch_all, reject_approval

router = APIRouter(prefix="/api/approvals", tags=["approvals"],
                   dependencies=[Depends(require_approver)])


class Decision(BaseModel):
    approver: str = "demo-approver"


@router.get("")
def list_approvals(state: str = "pending") -> list[dict]:
    """Pending items with full context for the reviewer: order, amount, policy reason,
    and the agent's rationale."""
    return fetch_all(
        """
        SELECT a.approval_id, a.order_id, a.action, a.amount_cents, a.policy_version,
               a.policy_reason, a.agent_rationale, a.state, a.created_at,
               o.item, o.currency, c.name AS customer_name
        FROM approvals a
        JOIN orders o ON o.order_id = a.order_id
        JOIN customers c ON c.customer_id = o.customer_id
        WHERE a.state = %s
        ORDER BY a.approval_id
        """,
        (state,),
    )


@router.post("/{approval_id}/approve")
def approve(approval_id: int, body: Decision) -> dict:
    return execute_approval(approval_id, body.approver)


@router.post("/{approval_id}/reject")
def reject(approval_id: int, body: Decision) -> dict:
    return reject_approval(approval_id, body.approver)
