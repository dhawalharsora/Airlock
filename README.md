# Airlock — a control plane for high-risk AI agents

![Airlock overview: customer request → agent tools → policy gate → human approval → execute and audit](media/Airlock_overview.png)

Most AI agent demos stop at "it can chat." The hard part is everything that has to
be true before an agent is allowed to take a **real, consequential action** — move
money, change a booking, cancel an order.

**Airlock is the governance layer that sits *behind* an agent and makes those actions
safe to ship.** It is deliberately **model- and vendor-agnostic**: the agent can run on
Bedrock, OpenAI, or a local model (swap with one env flag) — Airlock is the part that
decides, gates, audits, and measures what that agent is allowed to actually do.

The star of this repo is the **policy engine + human approval gate + refusal evals +
release gate**, not the chatbot. A customer-operations refund agent is the vehicle,
chosen because refunds move (fake) money — which forces every safety mechanism to be real.

> Synthetic business data, real system. Everything above the data layer runs for real.

[![Watch the Airlock introduction](media/Airlock_Intro_M-thumbnail.jpg)](media/Airlock_Intro_M.mp4?raw=1)

[▶ Watch the Airlock introduction](media/Airlock_Intro_M.mp4?raw=1)

## What makes an action "safe to ship" here

- **Policy-aware decisions** — approve / refuse / escalate resolved deterministically
  against a *versioned* policy, in code, not by the model's mood.
- **A human airlock** — high-risk tools can only *queue* a pending action; they
  physically cannot execute. A human approves, and only then does it run.
- **Defense in depth** — the gate re-checks policy itself, so a jailbroken or
  hallucinating agent still can't push through an ineligible refund.
- **Immutable audit** — every decision and action is an append-only row (enforced in
  the DB), so the system is accountable.
- **PII redaction at the boundary** — observability never becomes a data leak.
- **Refusal evals + release gate** — safety is *measured*: a suite of adversarial
  cases, and CI that blocks a change which regresses the safety invariants.

## Repository layout

| Path | What lives here |
|---|---|
| `agent/`       | Agent loop (Strands) + provider interface (Bedrock / OpenAI / Ollama) + the customer HTTP service |
| `mcp-server/`  | FastMCP tool server over HTTP: `get_order`, `lookup_policy`, `issue_refund`… + **PII redaction** + the **high-risk gate** |
| `api/`         | FastAPI backend: approval queue + observability endpoints |
| `web/`         | React + TypeScript (Vite): Customer, Approval queue, Observability |
| `db/`          | Postgres schema (`migrations/`) and synthetic seed data (`seed/`) |
| `policies/`    | Versioned refund policies — deterministic, not RAG |
| `evals/`       | Refusal-weighted eval suite (live agent) + LLM-as-judge |
| `infra/`       | Terraform (AWS) and Docker assets |
| `.github/`     | CI — deterministic safety tests gate every PR; live evals run nightly |

## See Airlock in action

Watch the complete browser workflow: a customer request, the agent's decision, human
approval, execution, and observability.

[![Watch the Airlock agent demo](media/Airlock_Agent_Demo-thumbnail.jpg)](media/Airlock_Agent_Demo.mp4?raw=1)

[▶ Watch the agent workflow](media/Airlock_Agent_Demo.mp4?raw=1)

## Run it

**One command — the whole stack:**

```bash
./scripts/dev.sh
```

This brings everything up in dependency order in a single terminal —
Postgres (Docker) → MCP tool server (`:8081`) → agent service (`:8100`) →
API (`:8000`) → web (`:5173`) — streaming each service's logs with a coloured
`[name]` prefix. Open **http://localhost:5173** for the full demo. `Ctrl+C`
tears the whole stack down cleanly.

Prerequisites: `docker`, `uv`, `npm`, and a model provider. For the free/local
path, run `ollama serve` + `ollama pull qwen2.5:7b` and set `MODEL_PROVIDER=ollama`
in `.env` (already the default).

Prefer to bring services up by hand (or run just one)? See [`RUN.md`](RUN.md) for the
full step-by-step walkthrough — Postgres, MCP server, agent service, API, and web,
plus provider setup and DB verification queries. The end-to-end demo (customer
request → agent decision → human approval → execution → observability) runs entirely
in the browser.

[![Watch the Airlock console demo](media/Airlock_Console_Demo-thumbnail.jpg)](media/Airlock_Console_Demo.mp4?raw=1)

[▶ Watch Airlock start from the console](media/Airlock_Console_Demo.mp4?raw=1)

## Evaluate safety

Run the refusal-weighted eval suite to verify that the agent approves eligible
requests, refuses ineligible ones, and escalates ambiguous cases:

```bash
cd evals
uv run python runner.py
```

[![Watch the Airlock evaluation demo](media/Airlock_Eval_Demo-thumbnail.jpg)](media/Airlock_Eval_Demo.mp4?raw=1)

[▶ Watch the safety evaluation](media/Airlock_Eval_Demo.mp4?raw=1)
