"""Core agent runs, shared by the CLI, the sync HTTP endpoint, and streaming.

Multi-turn: callers pass prior `history` (the conversation) and get updated history
back, so the bot remembers the thread. Safety is unchanged and per-turn:
- ownership is checked on every message before the agent runs;
- the gate re-validates policy on every tool call and never trusts history.
Action turns show the SYSTEM's ground-truth outcome; info turns show the bot's text.
"""
import json
import os
import re
import time

import psycopg
from dotenv import load_dotenv
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp import MCPClient

from airlock_agent.observability import record_run
from airlock_agent.providers import get_model

load_dotenv()

MCP_URL = os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8081/mcp/")
AGENT_MODEL = os.environ.get("AGENT_MODEL", "ollama")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://airlock:airlock@localhost:5432/airlock"
)

ACTION_TOOLS = {"issue_refund", "issue_replacement", "escalate"}

SYSTEM_PROMPT = (
    "You are a customer-operations assistant for Southern Cross Airways, a fictional "
    "airline used for this demo. You can (a) ANSWER questions about the refund policy "
    "or an order's eligibility, and (b) HANDLE a refund request.\n\n"
    "First decide the customer's intent:\n"
    "- If they are only ASKING (e.g. 'is this refundable?', 'what's your policy?', 'why?'):"
    " use get_order / lookup_policy to check, then EXPLAIN what the policy says and what "
    "WOULD happen (auto-approve / needs human review / not eligible), and offer to proceed. "
    "Do NOT call issue_refund or escalate, and do NOT claim any action was taken.\n"
    "- If they clearly want to ACT (e.g. 'refund it', 'yes, submit', 'I'd like a refund for "
    "ORD-...'), follow these steps IN ORDER:\n"
    "    1. Call get_order.\n"
    "    2. Call lookup_policy to get the governed recommendation.\n"
    "    3. Take the matching action by CALLING A TOOL:\n"
    "       - approve  -> call issue_refund with the refundable amount.\n"
    "       - escalate -> call escalate with the reason.\n"
    "       - refuse   -> explain the reason (no tool call).\n\n"
    "Hard rules:\n"
    "- NEVER say something was refunded, queued, or escalated unless you actually called "
    "the matching tool THIS turn.\n"
    "- NEVER issue a refund when the recommendation is refuse or escalate.\n"
    "- issue_refund only QUEUES a refund for human approval; never say a refund is processed "
    "or credited.\n"
    "- Never invent order or policy details."
)

_ORD_RE = re.compile(r"ORD-\d+", re.IGNORECASE)


def _order_refs(message: str) -> set[str]:
    return {m.upper() for m in _ORD_RE.findall(message)}


def _owned_orders(customer_id: str) -> set[str]:
    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute("SELECT order_id FROM orders WHERE customer_id = %s", (customer_id,))
        return {r[0] for r in cur.fetchall()}


def _ownership_violation(message: str, customer_id: str | None) -> str | None:
    if not customer_id:
        return None
    owned = _owned_orders(customer_id)
    for oid in _order_refs(message):
        if oid not in owned:
            return oid
    return None


def _denied(order_id: str) -> dict:
    return {"final": "refused", "pill": "refuse", "approval_id": None,
            "reason": "ownership check failed",
            "customer_message": f"Order {order_id} isn't on your account, so I can't act on it.",
            "order": {"order_id": order_id, "item": None, "amount_cents": None,
                      "currency": "AUD", "customer_name": None, "status": None},
            "policy": {"recommendation": None, "version": None, "reason": "not your order"}}


def _connect():
    return get_model(), MCPClient(lambda: streamablehttp_client(MCP_URL))


def _tool_io(agent) -> tuple[list[str], dict]:
    id_to_name, calls, results = {}, [], {}
    for msg in agent.messages:
        for b in (msg.get("content") or []):
            if isinstance(b, dict) and "toolUse" in b:
                tu = b["toolUse"]
                id_to_name[tu.get("toolUseId")] = tu.get("name")
                calls.append(tu.get("name"))
    for msg in agent.messages:
        for b in (msg.get("content") or []):
            if isinstance(b, dict) and "toolResult" in b:
                tr = b["toolResult"]
                name = id_to_name.get(tr.get("toolUseId"))
                if not name:
                    continue
                val = None
                for c in (tr.get("content") or []):
                    if isinstance(c, dict):
                        if "json" in c:
                            val = c["json"]
                        elif "text" in c:
                            try:
                                val = json.loads(c["text"])
                            except Exception:  # noqa: BLE001
                                val = c["text"]
                if val is not None:
                    results[name] = val
    return calls, results


def _final_text(agent) -> str:
    for msg in reversed(agent.messages):
        if msg.get("role") == "assistant":
            parts = [b.get("text", "") for b in (msg.get("content") or [])
                     if isinstance(b, dict) and "text" in b]
            if parts:
                return "".join(parts).strip()
    return ""


def _outcome(results: dict) -> dict:
    order = results.get("get_order") or {}
    policy = results.get("lookup_policy") or {}
    refund = results.get("issue_refund") or results.get("issue_replacement") or {}
    esc = results.get("escalate") or {}

    if refund.get("status") == "pending_approval":
        final, approval_id = "queued", refund.get("approval_id")
    elif refund.get("status") == "blocked":
        final, approval_id = "refused", None
    elif esc.get("status") == "escalated":
        final, approval_id = "escalated", esc.get("approval_id")
    else:
        final, approval_id = "refused", None

    reason = policy.get("reason") or refund.get("reason") or ""
    item, amount = order.get("item"), order.get("amount_cents")
    ccy, oid = order.get("currency", "AUD"), order.get("order_id")

    def m(cents):
        return f"{ccy} {cents/100:.2f}" if isinstance(cents, (int, float)) else "the amount"

    if final == "queued":
        msg = (f"Your refund of {m(amount)} for {item} (order {oid}) has been queued for "
               f"human approval. Nothing has been charged back yet.")
    elif final == "escalated":
        msg = (f"Your refund request for {item} (order {oid}) needs a manual review and has "
               f"been escalated to our team.")
    else:
        msg = f"We're unable to refund {item} (order {oid}): {reason}"

    pill = {"queued": "approve", "escalated": "escalate", "refused": "refuse"}[final]
    return {"final": final, "pill": pill, "approval_id": approval_id, "reason": reason,
            "customer_message": msg,
            "order": {"order_id": oid, "item": item, "amount_cents": amount,
                      "currency": ccy, "customer_name": order.get("customer_name"),
                      "status": order.get("status")},
            "policy": {"recommendation": policy.get("recommendation"),
                       "version": policy.get("policy_version"), "reason": reason,
                       "checks": policy.get("checks") or [],
                       "window_days": policy.get("window_days"),
                       "cap_cents": policy.get("cap_cents"),
                       "age_days": policy.get("age_days")}}


def _usage(result):
    try:
        u = result.metrics.accumulated_usage
        return u.get("inputTokens", 0), u.get("outputTokens", 0)
    except Exception:  # noqa: BLE001
        return 0, 0


def _denied_history(history, message, denied):
    h = list(history or [])
    h.append({"role": "user", "content": [{"text": message}]})
    h.append({"role": "assistant", "content": [{"text": denied["customer_message"]}]})
    return h


def run_agent(message: str, customer_id: str | None = None, history: list | None = None) -> dict:
    bad = _ownership_violation(message, customer_id)
    if bad:
        outcome = _denied(bad)
        run_id = record_run(message, "refuse", AGENT_MODEL, 0, 0, 0, [])
        return {"is_action": True, "outcome": outcome, "reply": outcome["customer_message"],
                "tool_calls": [], "run_id": run_id, "tokens_in": 0, "tokens_out": 0,
                "latency_ms": 0, "history": _denied_history(history, message, outcome)}

    model, client = _connect()
    with client:
        tools = client.list_tools_sync()
        agent = Agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT, messages=history or [])
        started = time.time()
        result = agent(message)
        latency_ms = int((time.time() - started) * 1000)
        calls, results = _tool_io(agent)
        reply = _final_text(agent)
        updated = list(agent.messages)

    is_action = bool(set(calls) & ACTION_TOOLS)
    outcome = _outcome(results)
    tin, tout = _usage(result)
    run_id = record_run(message, outcome["pill"] if is_action else "info",
                        AGENT_MODEL, tin, tout, latency_ms, calls)
    return {"is_action": is_action, "outcome": outcome, "reply": reply, "tool_calls": calls,
            "run_id": run_id, "tokens_in": tin, "tokens_out": tout, "latency_ms": latency_ms,
            "history": updated}


async def astream_agent(message: str, customer_id: str | None = None, history: list | None = None):
    yield {"type": "start"}

    bad = _ownership_violation(message, customer_id)
    if bad:
        outcome = _denied(bad)
        run_id = record_run(message, "refuse", AGENT_MODEL, 0, 0, 0, [])
        yield {"type": "done", "is_action": True, "outcome": outcome,
               "reply": outcome["customer_message"], "tool_calls": [], "run_id": run_id,
               "tokens_in": 0, "tokens_out": 0, "latency_ms": 0}
        yield {"type": "_session", "history": _denied_history(history, message, outcome)}
        return

    model, client = _connect()
    with client:
        tools = client.list_tools_sync()
        agent = Agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT, messages=history or [])
        seen, result = [], None
        started = time.time()
        async for event in agent.stream_async(message):
            if "data" in event:
                yield {"type": "token", "text": event["data"]}
            if "current_tool_use" in event:
                name = event["current_tool_use"].get("name")
                if name and name not in seen:
                    seen.append(name)
                    yield {"type": "tool", "name": name}
            if "result" in event:
                result = event["result"]
        latency_ms = int((time.time() - started) * 1000)
        calls, results = _tool_io(agent)
        reply = _final_text(agent)
        updated = list(agent.messages)

    is_action = bool(set(calls) & ACTION_TOOLS)
    outcome = _outcome(results)
    tin, tout = _usage(result) if result else (0, 0)
    run_id = record_run(message, outcome["pill"] if is_action else "info",
                        AGENT_MODEL, tin, tout, latency_ms, calls)
    yield {"type": "done", "is_action": is_action, "outcome": outcome, "reply": reply,
           "tool_calls": calls, "run_id": run_id, "tokens_in": tin, "tokens_out": tout,
           "latency_ms": latency_ms}
    yield {"type": "_session", "history": updated}
