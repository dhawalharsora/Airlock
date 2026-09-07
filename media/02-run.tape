# Video 2 — "Running it": how Airlock actually comes up and proves itself.
# Render from the repo root:  vhs media/02-run.tape   ->   media/02-run.mp4
# Needs: Docker running, Ollama running (`ollama serve`) with the model pulled
#        (`ollama pull qwen2.5:7b`).  Provider is set to ollama in .env.

Output media/02-run.mp4

Require docker
Require uv

# ---- look & feel: matches the intro deck (dark + teal, IBM Plex Mono) ----
Set Shell "zsh"
Set FontFamily "IBM Plex Mono"
Set FontSize 18
Set Width 1500
Set Height 900
Set Padding 28
Set Margin 46
Set MarginFill "#070a0e"
Set BorderRadius 12
Set WindowBar Colorful
Set TypingSpeed 28ms
Set Theme { "name":"Airlock","background":"#0b0f14","foreground":"#e9eef3","cursor":"#2bb7b1","selection":"#1b232c","black":"#151b23","red":"#f0685e","green":"#3ac47d","yellow":"#e0a63c","blue":"#7fe0db","magenta":"#b58cff","cyan":"#2bb7b1","white":"#93a1af","brightBlack":"#33424e","brightRed":"#f0685e","brightGreen":"#3ac47d","brightYellow":"#e0a63c","brightBlue":"#7fe0db","brightMagenta":"#b58cff","brightCyan":"#7fe0db","brightWhite":"#e9eef3" }

# ---- silent setup (hidden from the recording) ----
Hide
Type "cd $(git rev-parse --show-toplevel 2>/dev/null || echo .)" Enter
Type "setopt interactive_comments" Enter
Type "clear" Enter
Show

Sleep 1s
Type "# Airlock runs as a few small services. Here's the whole thing, from zero." Sleep 700ms Enter
Sleep 1s

Type "# 1) Postgres — schema + synthetic seed load on first boot" Sleep 500ms Enter
Type "docker compose up -d --wait db" Enter
Wait+Screen@90s /(Healthy|Running|Started)/
Sleep 1500ms

Type "# The seeded orders our refund agent reasons about" Sleep 500ms Enter
Type `docker compose exec -T db psql -U airlock -d airlock -c "SELECT order_id, amount_cents, status FROM orders;"` Enter
Sleep 3s

Type "# 2) The safety logic is pure & deterministic — tested with NO model" Sleep 500ms Enter
Type "cd mcp-server && uv run pytest tests -q; cd .." Enter
Wait+Screen@180s /passed/
Sleep 2500ms

Type "# 3) Start the FastMCP tool server (get_order, lookup_policy, issue_refund)" Sleep 500ms Enter
Type "(cd mcp-server && uv run python -m airlock_mcp.server > /tmp/airlock-mcp.log 2>&1) &" Enter
Sleep 7s
Type "# ...serving on http://127.0.0.1:8081/mcp/" Sleep 500ms Enter
Sleep 1s

Type "# 4) One real request: refund ORD-1002 → agent decides, then QUEUES it" Sleep 500ms Enter
Type "cd agent && uv run --extra ollama python -m airlock_agent.main ORD-1002; cd .." Enter
Sleep 45s

Type "# Proof: the money did NOT move — it's a PENDING approval awaiting a human" Sleep 500ms Enter
Type `docker compose exec -T db psql -U airlock -d airlock -c "SELECT approval_id, order_id, action, state FROM approvals ORDER BY approval_id DESC LIMIT 3;"` Enter
Sleep 3500ms

Type "# Every decision lands in an append-only audit log — nothing happens off the record" Sleep 500ms Enter
Type `docker compose exec -T db psql -U airlock -d airlock -c "SELECT actor, action, outcome, policy_version FROM audit_log ORDER BY audit_id DESC LIMIT 5;"` Enter
Sleep 4s

Type "# One system. Real data path. Human-gated at every consequential step." Sleep 500ms Enter
Sleep 3s

# ---- cleanup (hidden) ----
Hide
Type "pkill -f airlock_mcp.server 2>/dev/null; true" Enter
Show
Sleep 500ms
