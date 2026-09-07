-- Idempotency at the database: an order can have at most ONE executed refund.
-- Even if two stale approvals slip through, the DB physically rejects a second
-- executed refund for the same order (belt-and-suspenders with the app-level guard).
CREATE UNIQUE INDEX one_executed_refund_per_order
    ON refunds (order_id)
    WHERE status = 'executed';
