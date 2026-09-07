-- Airlock schema v1. Money is stored as INTEGER CENTS (never float) to avoid
-- rounding errors on values that move real money.

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL
);

CREATE TABLE orders (
    order_id     TEXT PRIMARY KEY,
    customer_id  TEXT NOT NULL REFERENCES customers(customer_id),
    item         TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    currency     TEXT NOT NULL DEFAULT 'AUD',
    status       TEXT NOT NULL DEFAULT 'completed',   -- completed | refunded | cancelled
    ordered_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Versioned policy. The agent resolves the EXACT applicable version, deterministically.
CREATE TABLE policy_versions (
    version            INTEGER PRIMARY KEY,
    name               TEXT NOT NULL,
    refund_window_days INTEGER NOT NULL,
    max_auto_refund_cents INTEGER NOT NULL,      -- above this, must escalate to a human
    rules              JSONB NOT NULL,
    active             BOOLEAN NOT NULL DEFAULT false,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE refunds (
    refund_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id       TEXT NOT NULL REFERENCES orders(order_id),
    amount_cents   INTEGER NOT NULL,
    policy_version INTEGER NOT NULL REFERENCES policy_versions(version),
    status         TEXT NOT NULL DEFAULT 'pending',  -- pending | executed | rejected
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The human airlock. High-risk actions land here as 'pending' and cannot self-execute.
CREATE TABLE approvals (
    approval_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id        TEXT NOT NULL REFERENCES orders(order_id),
    action          TEXT NOT NULL,                   -- issue_refund | issue_replacement
    amount_cents    INTEGER NOT NULL,
    policy_version  INTEGER NOT NULL REFERENCES policy_versions(version),
    policy_reason   TEXT NOT NULL,
    agent_rationale TEXT NOT NULL,
    state           TEXT NOT NULL DEFAULT 'pending', -- pending | approved | rejected
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at      TIMESTAMPTZ,
    decided_by      TEXT
);

-- Append-only audit trail. Immutability is ENFORCED below, not just by convention.
CREATE TABLE audit_log (
    audit_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor          TEXT NOT NULL,                    -- agent | approver:<name> | system
    action         TEXT NOT NULL,
    entity         TEXT,
    entity_id      TEXT,
    inputs         JSONB,
    outcome        TEXT,
    policy_version INTEGER,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Observability: one row per agent run, one row per step (token/latency/cost).
CREATE TABLE runs (
    run_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    prompt     TEXT NOT NULL,
    decision   TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE run_steps (
    step_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id      BIGINT NOT NULL REFERENCES runs(run_id),
    step_no     INTEGER NOT NULL,
    tool        TEXT,
    tokens_in   INTEGER DEFAULT 0,
    tokens_out  INTEGER DEFAULT 0,
    latency_ms  INTEGER DEFAULT 0,
    cost_usd    NUMERIC(10,6) DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enforce append-only on audit_log: block UPDATE and DELETE at the DB layer.
CREATE OR REPLACE FUNCTION airlock_block_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only: % is not allowed', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_no_update BEFORE UPDATE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION airlock_block_mutation();
CREATE TRIGGER audit_log_no_delete BEFORE DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION airlock_block_mutation();
