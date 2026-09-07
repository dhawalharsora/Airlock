"""Agent HTTP service — the customer entry point (multi-turn).

- POST /agent/handle : sync run, returns the ground-truth outcome + reply.
- POST /agent/stream : streams token deltas + tool calls (NDJSON), then the outcome.

Per-session conversation is kept in-memory (session_id -> history). Ownership is
checked every turn and the gate re-validates policy on every tool call — neither
depends on conversation history. Durable / cross-session memory is out of scope.
"""
import json

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from airlock_agent.core import astream_agent, run_agent

load_dotenv()

app = FastAPI(title="Airlock Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)

# In-memory conversation store: session_id -> history (list of messages).
SESSIONS: dict[str, list] = {}


class Message(BaseModel):
    message: str
    customer_id: str | None = None
    session_id: str | None = None


@app.post("/agent/handle")
def handle(body: Message) -> dict:
    history = SESSIONS.get(body.session_id or "")
    out = run_agent(body.message, body.customer_id, history)
    if body.session_id:
        SESSIONS[body.session_id] = out.pop("history", None) or []
    else:
        out.pop("history", None)
    return out


@app.post("/agent/stream")
async def stream(body: Message) -> StreamingResponse:
    history = SESSIONS.get(body.session_id or "")

    async def ndjson():
        async for event in astream_agent(body.message, body.customer_id, history):
            if event.get("type") == "_session":
                if body.session_id:
                    SESSIONS[body.session_id] = event.get("history") or []
                continue  # internal — never sent to the client
            yield json.dumps(event) + "\n"

    return StreamingResponse(ndjson(), media_type="application/x-ndjson")


@app.post("/agent/reset")
def reset(body: Message) -> dict:
    SESSIONS.pop(body.session_id or "", None)
    return {"ok": True}


@app.get("/agent/health")
def health() -> dict:
    return {"ok": True}
