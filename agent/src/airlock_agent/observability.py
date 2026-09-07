"""Records each agent run to Postgres so the observability dashboard shows real
token / latency / cost numbers. The agent records its own run — observability is
'see what the agent is doing and spending', so the agent is the natural source."""
import os

import psycopg

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://airlock:airlock@localhost:5432/airlock"
)

# Rough per-1M-token prices (USD). Local models are free; Bedrock priced.
PRICES = {
    "haiku": (0.80, 4.00),
    "sonnet": (3.00, 15.00),
    "nova-lite": (0.06, 0.24),
}


def _cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    for key, (pin, pout) in PRICES.items():
        if key in (model or "").lower():
            return round(tokens_in / 1e6 * pin + tokens_out / 1e6 * pout, 6)
    return 0.0  # local / unknown model


def record_run(prompt: str, decision: str, model: str, tokens_in: int,
               tokens_out: int, latency_ms: int, tool_calls: list[str]) -> int | None:
    """Insert one run + its steps. Best-effort: never breaks the agent on failure."""
    try:
        cost = _cost_usd(model, tokens_in, tokens_out)
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO runs (prompt, decision) VALUES (%s,%s) RETURNING run_id",
                (prompt, decision),
            )
            run_id = cur.fetchone()[0]
            # one step per tool call (sequence), then a model step carrying the totals
            step_no = 1
            for tool in tool_calls:
                cur.execute(
                    "INSERT INTO run_steps (run_id, step_no, tool) VALUES (%s,%s,%s)",
                    (run_id, step_no, tool),
                )
                step_no += 1
            cur.execute(
                """INSERT INTO run_steps
                   (run_id, step_no, tool, tokens_in, tokens_out, latency_ms, cost_usd)
                   VALUES (%s,%s,'model',%s,%s,%s,%s)""",
                (run_id, step_no, tokens_in, tokens_out, latency_ms, cost),
            )
            conn.commit()
            return run_id
    except Exception as exc:  # noqa: BLE001
        print(f"(run not recorded: {exc})")
        return None
