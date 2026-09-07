# Run Airlock

## Prerequisites

- Docker
- `uv`
- Node.js and `npm`
- One model provider:
  - Bedrock: AWS credentials with access to the configured model and region.
  - Ollama: Ollama running locally with a compatible model available.
  - OpenAI: an OpenAI API key.

Copy `.env.example` to `.env` and choose a provider with `MODEL_PROVIDER`:

```bash
cp .env.example .env
```

For Ollama, start the local server and set `MODEL_PROVIDER=ollama` in `.env`:

```bash
ollama serve
ollama pull llama3.1
```

## Start Everything

From the repository root:

```bash
./scripts/dev.sh
```

Open the web app at <http://localhost:5173>.

The launcher starts the services in this order:

| Service | Address |
|---|---|
| Postgres | `localhost:5432` |
| MCP server | `http://localhost:8081/mcp/` |
| Agent service | `http://localhost:8100` |
| API service | `http://localhost:8000` |
| Web app | `http://localhost:5173` |

Press `Ctrl+C` to stop the application services. Postgres remains running; stop it
separately when needed:

```bash
docker compose stop db
```

Logs from the launcher are written to `logs/`.

## Start Services Manually

Run each service in a separate terminal from the repository root.

### Postgres

```bash
docker compose up -d db
```

The schema and seed data are created when the database volume is initialized.

### MCP server

```bash
cd mcp-server
uv sync
uv run python -m airlock_mcp.server
```

### Agent service

```bash
cd agent
uv sync --extra ollama
uv run uvicorn airlock_agent.server:app --port 8100
```

### API service

```bash
cd api
uv sync
uv run uvicorn airlock_api.main:app --port 8000
```

### Web app

```bash
cd web
npm install
npm run dev
```

Open <http://localhost:5173> after all services are running.

## Run the Agent from the CLI

With Postgres, the MCP server, and a model provider running:

```bash
cd agent
uv run python -m airlock_agent.main ORD-1002
```

The order ID is optional. The default is `ORD-1001`.

## Health Checks

```bash
curl http://localhost:8100/agent/health
curl http://localhost:8000/api/health
```

## Reset Local Database

To remove the local Postgres data and recreate the schema and seed data:

```bash
docker compose down -v
docker compose up -d db
```
