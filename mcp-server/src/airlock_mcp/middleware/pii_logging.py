"""Boundary logging middleware.

Every tool call is logged here for observability — arguments AND results — and every
logged record is redacted first. Because this sits at the MCP boundary, redaction
covers ALL tools and any future client, not one code path. A customer email fetched
by a tool shows up in the trace as ***REDACTED***, never in the clear.
"""
import json
import os
from datetime import datetime, timezone

from fastmcp.server.middleware import Middleware, MiddlewareContext

from airlock_mcp.redaction import redact

TRACE_LOG = os.environ.get("MCP_TRACE_LOG", "traces.log")


def _result_view(result) -> object:
    """Best-effort JSON-able view of a tool result, for redacted logging."""
    try:
        sc = getattr(result, "structured_content", None)
        if sc is not None:
            return sc
        blocks = getattr(result, "content", None) or []
        texts = [getattr(b, "text", None) for b in blocks]
        texts = [t for t in texts if t]
        return texts if texts else None
    except Exception:  # noqa: BLE001
        return None


class PIIRedactionMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        result = await call_next(context)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": context.message.name,
            "arguments": redact(dict(context.message.arguments or {})),
            "result": redact(_result_view(result)),
        }
        try:
            with open(TRACE_LOG, "a") as fh:
                fh.write(json.dumps(record) + "\n")
        except Exception:  # noqa: BLE001
            pass
        return result
