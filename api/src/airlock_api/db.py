"""DB helpers for the API. Includes audit writes for human (approver) actions."""
import json
import os

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://airlock:airlock@localhost:5432/airlock"
)


def _connect():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def write_audit(actor, action, entity, entity_id, inputs, outcome, policy_version):
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO audit_log (actor, action, entity, entity_id, inputs, outcome, policy_version)
               VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s)""",
            (actor, action, entity, entity_id, json.dumps(inputs or {}), outcome, policy_version),
        )
        conn.commit()


def execute_approval(approval_id: int, approver: str) -> dict:
    """Approve a pending high-risk action: mark approved, EXECUTE the refund on the
    order, record the refund, and audit — all in one transaction."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM approvals WHERE approval_id=%s", (approval_id,))
        appr = cur.fetchone()
        if appr is None:
            return {"error": "not_found"}
        if appr["state"] != "pending":
            return {"error": "not_pending", "state": appr["state"]}

        cur.execute("SELECT amount_cents, status FROM orders WHERE order_id=%s", (appr["order_id"],))
        order = cur.fetchone()
        amount = appr["amount_cents"] or (order["amount_cents"] if order else 0)

        # Idempotency guard: an order is refunded at most once. If it already is,
        # clear this (stale) approval without issuing a second refund, and audit it.
        if order and order["status"] == "refunded":
            cur.execute(
                "UPDATE approvals SET state='approved', decided_at=now(), decided_by=%s WHERE approval_id=%s",
                (approver, approval_id),
            )
            cur.execute(
                """INSERT INTO audit_log (actor, action, entity, entity_id, inputs, outcome, policy_version)
                   VALUES (%s,'execute_refund','approval',%s,%s::jsonb,'noop_already_refunded',%s)""",
                (f"approver:{approver}", str(approval_id),
                 json.dumps({"amount_cents": amount}), appr["policy_version"]),
            )
            conn.commit()
            return {"status": "already_refunded", "approval_id": approval_id,
                    "note": "Order was already refunded — no second refund issued."}

        cur.execute(
            "UPDATE approvals SET state='approved', decided_at=now(), decided_by=%s WHERE approval_id=%s",
            (approver, approval_id),
        )
        cur.execute("UPDATE orders SET status='refunded' WHERE order_id=%s", (appr["order_id"],))
        cur.execute(
            """INSERT INTO refunds (order_id, amount_cents, policy_version, status)
               VALUES (%s,%s,%s,'executed')""",
            (appr["order_id"], amount, appr["policy_version"]),
        )
        cur.execute(
            """INSERT INTO audit_log (actor, action, entity, entity_id, inputs, outcome, policy_version)
               VALUES (%s,'execute_refund','approval',%s,%s::jsonb,'executed',%s)""",
            (f"approver:{approver}", str(approval_id),
             json.dumps({"amount_cents": amount}), appr["policy_version"]),
        )
        conn.commit()
        return {"status": "executed", "approval_id": approval_id, "amount_cents": amount}


def reject_approval(approval_id: int, approver: str) -> dict:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT state FROM approvals WHERE approval_id=%s", (approval_id,))
        row = cur.fetchone()
        if row is None:
            return {"error": "not_found"}
        if row["state"] != "pending":
            return {"error": "not_pending", "state": row["state"]}
        cur.execute(
            "UPDATE approvals SET state='rejected', decided_at=now(), decided_by=%s WHERE approval_id=%s",
            (approver, approval_id),
        )
        cur.execute(
            """INSERT INTO audit_log (actor, action, entity, entity_id, inputs, outcome, policy_version)
               VALUES (%s,'reject_refund','approval',%s,'{}'::jsonb,'rejected',NULL)""",
            (f"approver:{approver}", str(approval_id)),
        )
        conn.commit()
        return {"status": "rejected", "approval_id": approval_id}
