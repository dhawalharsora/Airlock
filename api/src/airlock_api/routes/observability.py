"""Observability: per-run traces with token / latency / cost, plus a summary."""
from fastapi import APIRouter, Depends

from airlock_api.auth import require_approver
from airlock_api.db import fetch_all, fetch_one

router = APIRouter(prefix="/api", tags=["observability"],
                   dependencies=[Depends(require_approver)])


@router.get("/runs")
def list_runs(limit: int = 50) -> list[dict]:
    runs = fetch_all(
        """
        SELECT r.run_id, r.prompt, r.decision, r.created_at,
               COALESCE(SUM(s.tokens_in),0)  AS tokens_in,
               COALESCE(SUM(s.tokens_out),0) AS tokens_out,
               COALESCE(SUM(s.latency_ms),0) AS latency_ms,
               COALESCE(SUM(s.cost_usd),0)   AS cost_usd
        FROM runs r LEFT JOIN run_steps s ON s.run_id = r.run_id
        GROUP BY r.run_id ORDER BY r.run_id DESC LIMIT %s
        """,
        (limit,),
    )
    for r in runs:
        r["steps"] = fetch_all(
            "SELECT step_no, tool, tokens_in, tokens_out, latency_ms, cost_usd "
            "FROM run_steps WHERE run_id=%s ORDER BY step_no",
            (r["run_id"],),
        )
    return runs


@router.get("/metrics")
def metrics() -> dict:
    return fetch_one(
        """
        SELECT COUNT(*) AS runs,
               COALESCE(SUM(tokens_in),0)  AS tokens_in,
               COALESCE(SUM(tokens_out),0) AS tokens_out,
               COALESCE(SUM(cost_usd),0)   AS cost_usd
        FROM run_steps
        """
    ) or {}


@router.get("/audit")
def audit(limit: int = 12) -> list[dict]:
    return fetch_all(
        """SELECT audit_id, actor, action, entity_id, outcome, policy_version, created_at
           FROM audit_log ORDER BY audit_id DESC LIMIT %s""",
        (limit,),
    )


@router.get("/policies")
def policies() -> list[dict]:
    return fetch_all(
        """SELECT version, name, refund_window_days, max_auto_refund_cents, active
           FROM policy_versions ORDER BY version"""
    )
