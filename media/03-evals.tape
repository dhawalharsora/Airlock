# Video 3 — "Evals": safety is measured, and it gates the merge.
# Render from the repo root:  vhs media/03-evals.tape   ->   media/03-evals.mp4
# Needs: Docker (db), the MCP server on :8081, and Ollama running with the model.
#        The hidden setup block below brings db + mcp up for you.
#
# Live cases use evals/cases/refunds.demo.yaml (6 representative cases) so the
# tape stays watchable. The full 15-case suite is evals/cases/refunds.yaml.

Output media/03-evals.mp4

Require docker
Require uv

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

# ---- silent setup: repo root, db up, mcp server up, evals deps synced ----
Hide
Type "cd $(git rev-parse --show-toplevel 2>/dev/null || echo .)" Enter
Type "setopt interactive_comments" Enter
Type "docker compose up -d --wait db >/dev/null 2>&1" Enter
Sleep 2s
Type "(cd mcp-server && uv run python -m airlock_mcp.server > /tmp/airlock-mcp.log 2>&1) &" Enter
Sleep 7s
Type "cd evals && uv sync --extra ollama >/dev/null 2>&1; cd .." Enter
Sleep 2s
Type "clear" Enter
Show

Sleep 1s
Type "# Safety isn't asserted here — it's measured. Start with the adversarial cases." Sleep 700ms Enter
Sleep 1s
Type "sed -n '1,28p' evals/cases/refunds.demo.yaml" Enter
Sleep 4s

Type "# The MERGE GATE: deterministic policy + PII tests. No model. Runs on every PR." Sleep 500ms Enter
Type "cd mcp-server && uv run pytest tests -q; cd .." Enter
Sleep 8s

Type "# The LIVE refusal suite: every case run against the real agent." Sleep 500ms Enter
Type "# refusal_accuracy = % of refuse/escalate cases where it never touched the money." Sleep 500ms Enter
Type "cd evals && PYTHONUNBUFFERED=1 AIRLOCK_EVAL_CASES=cases/refunds.demo.yaml uv run --extra ollama python runner.py; cd .." Enter
Sleep 100s

Type "# Every adversarial case → refuse or escalate. Never a wrongful refund." Sleep 500ms Enter
Sleep 3s

Hide
Type "pkill -f airlock_mcp.server 2>/dev/null; true" Enter
Show
Sleep 500ms
