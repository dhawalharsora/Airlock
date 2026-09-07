"""DB helpers for the MCP tools. One connection per call.

Note: write_audit() runs its payload through redact() so PII never lands in the
audit store — the audit trail is a log, and logs must not leak PII.
"""
import json
import os

import psycopg
from psycopg.rows import dict_row

from airlock_mcp.redaction import redact

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://airlock:airlock@localhost:5432/airlock"
)


def _connect():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_active_policy() -> dict:
    return fetch_one("SELECT * FROM policy_versions WHERE active = true LIMIT 1")


def write_audit(actor: str, action: str, entity: str, entity_id: str,
                inputs: dict, outcome: str, policy_version: int | None) -> None:
    """Append one immutable audit row. Inputs are redacted before storage."""
    safe_inputs = json.dumps(redact(inputs or {}))
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_log (actor, action, entity, entity_id, inputs, outcome, policy_version)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
            """,
            (actor, action, entity, entity_id, safe_inputs, outcome, policy_version),
        )
        conn.commit()


def queue_approval(order_id: str, action: str, amount_cents: int, policy_version: int,
                   policy_reason: str, agent_rationale: str) -> int:
    """Write a PENDING row to the approval queue and return its id. Does NOT execute."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO approvals
              (order_id, action, amount_cents, policy_version, policy_reason, agent_rationale, state)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            RETURNING approval_id
            """,
            (order_id, action, amount_cents, policy_version, policy_reason, agent_rationale),
        )
        approval_id = cur.fetchone()["approval_id"]
        conn.commit()
        return approval_id
