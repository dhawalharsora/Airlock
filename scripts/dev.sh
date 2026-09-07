#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Airlock — one-command dev launcher
#
#   ./scripts/dev.sh
#
# Brings up the whole stack for the demo, in dependency order, in ONE terminal:
#   db (docker)  ->  mcp-server :8081  ->  agent :8100  ->  api :8000  ->  web :5173
#
# Every service logs to logs/<name>.log AND streams to this terminal with a
# coloured [name] prefix. Ctrl+C tears the whole stack down cleanly.
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
LOGDIR="$ROOT/logs"
mkdir -p "$LOGDIR"

# --- colours (fall back to empty strings if not a tty) ---------------------
if [ -t 1 ]; then
  C_DB=$'\033[36m'; C_MCP=$'\033[35m'; C_AGENT=$'\033[32m'
  C_API=$'\033[33m'; C_WEB=$'\033[34m'; C_ERR=$'\033[31m'; C_RST=$'\033[0m'
else
  C_DB=; C_MCP=; C_AGENT=; C_API=; C_WEB=; C_ERR=; C_RST=
fi

PIDS=()

log() { printf '%s\n' "$*"; }
die() { printf '%s%s%s\n' "$C_ERR" "$*" "$C_RST" >&2; exit 1; }

# Stream a background command's output to the terminal with a [name] prefix,
# tee'd to logs/<name>.log. Records the PID for cleanup.
run() {
  local name="$1" colour="$2"; shift 2
  local logfile="$LOGDIR/$name.log"
  : > "$logfile"
  ( "$@" 2>&1 | while IFS= read -r line; do
      printf '%s[%s]%s %s\n' "$colour" "$name" "$C_RST" "$line"
    done | tee -a "$logfile" ) &
  PIDS+=($!)
}

cleanup() {
  log ""
  log "${C_ERR}Shutting down…${C_RST}"
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  # kill anything still bound to our ports (uv/uvicorn/vite spawn children)
  for port in 8081 8100 8000 5173; do
    lsof -ti tcp:"$port" 2>/dev/null | xargs -r kill 2>/dev/null || true
  done
  # leave Postgres running (it's a shared container); comment in to stop it:
  # docker compose stop db >/dev/null 2>&1 || true
  wait 2>/dev/null || true
  log "${C_ERR}Down.${C_RST}"
}
trap cleanup INT TERM EXIT

# Wait until a TCP port accepts connections (timeout in seconds).
wait_port() {
  local host="$1" port="$2" timeout="${3:-40}" name="$4" i=0
  while ! (exec 3<>"/dev/tcp/$host/$port") 2>/dev/null; do
    i=$((i+1))
    [ "$i" -ge "$timeout" ] && die "Timed out waiting for $name on $host:$port"
    sleep 1
  done
  exec 3>&- 2>/dev/null || true
}

# --- preflight -------------------------------------------------------------
command -v docker >/dev/null || die "docker not found"
command -v uv     >/dev/null || die "uv not found"
command -v npm    >/dev/null || die "npm not found"

if grep -q '^MODEL_PROVIDER=ollama' .env 2>/dev/null; then
  command -v ollama >/dev/null || die "MODEL_PROVIDER=ollama but ollama not found"
  curl -sf http://localhost:11434/api/tags >/dev/null 2>&1 \
    || die "Ollama isn't running. Start it (\`ollama serve\`) and pull the model first."
fi

# --- 1. Postgres -----------------------------------------------------------
log "${C_DB}[db]${C_RST} starting Postgres (docker compose up -d db)…"
docker compose up -d db >/dev/null
wait_port 127.0.0.1 5432 40 "Postgres"
log "${C_DB}[db]${C_RST} up on :5432"

# --- 2. deps (first run only — cheap no-ops afterwards) --------------------
log "syncing deps…"
( cd mcp-server && uv sync -q )
( cd agent      && uv sync -q --extra ollama )
( cd api        && uv sync -q )
[ -d web/node_modules ] || ( cd web && npm install --silent )

# --- 3. MCP tool server :8081 ----------------------------------------------
run mcp "$C_MCP" bash -c 'cd "'"$ROOT"'/mcp-server" && exec uv run python -m airlock_mcp.server'
wait_port 127.0.0.1 8081 40 "MCP server"
log "${C_MCP}[mcp]${C_RST} up on :8081"

# --- 4. Agent service :8100 ------------------------------------------------
run agent "$C_AGENT" bash -c 'cd "'"$ROOT"'/agent" && exec uv run uvicorn airlock_agent.server:app --port 8100'
wait_port 127.0.0.1 8100 40 "Agent service"
log "${C_AGENT}[agent]${C_RST} up on :8100"

# --- 5. API :8000 ----------------------------------------------------------
run api "$C_API" bash -c 'cd "'"$ROOT"'/api" && exec uv run uvicorn airlock_api.main:app --port 8000'
wait_port 127.0.0.1 8000 40 "API"
log "${C_API}[api]${C_RST} up on :8000"

# --- 6. Web :5173 ----------------------------------------------------------
run web "$C_WEB" bash -c 'cd "'"$ROOT"'/web" && exec npm run dev'
wait_port 127.0.0.1 5173 40 "Web"

log ""
log "${C_WEB}────────────────────────────────────────────────────────${C_RST}"
log "  Airlock is up  →  ${C_WEB}http://localhost:5173${C_RST}"
log "  logs: $LOGDIR/*.log   |   Ctrl+C to stop everything"
log "${C_WEB}────────────────────────────────────────────────────────${C_RST}"

wait
