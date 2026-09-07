"""Airlock API — serves the approval queue and observability dashboard."""
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from airlock_api.routes import approvals, customers, observability

load_dotenv()

app = FastAPI(title="Airlock API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(approvals.router)
app.include_router(observability.router)
app.include_router(customers.router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
