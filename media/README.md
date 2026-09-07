# Airlock — video series (silent + background music)

Four short videos for the repo home page. All share one look (dark + teal, IBM Plex),
so they feel like one product.

| # | Video | Source | Output |
|---|-------|--------|--------|
| 1 | Intro | `intro/index.html` (animated deck) | screen-record fullscreen |
| 2 | Running it | `media/02-run.tape` (VHS) | `media/02-run.mp4` |
| 3 | Evals | `media/03-evals.tape` (VHS) | `media/03-evals.mp4` |
| 4 | The journey (demo) | `media/04-demo-storyboard.md` | screen-record the browser |

## Prerequisites for the terminal tapes (2 & 3)
```bash
# model provider (local, deterministic, free)
ollama serve            # in its own terminal
ollama pull qwen2.5:7b  # once

# .env already has MODEL_PROVIDER=ollama
```
Docker and `uv` must be on PATH (they are). Run VHS from the **repo root**.

## Render the tapes
```bash
vhs media/02-run.tape     # -> media/02-run.mp4
vhs media/03-evals.tape   # -> media/03-evals.mp4
```
The tapes use `Wait+Screen` so they wait for real output instead of guessing at
model latency. First render of tape 2 may be slower if `uv` builds venvs — that's
one-time; re-render for the clean take.

Tape 3 uses `evals/cases/refunds.demo.yaml` (6 representative cases) so the
render stays watchable. The full 15-case suite is still `evals/cases/refunds.yaml`.

## Then, in Canva
Drop each MP4 in, add a royalty-free track (Audio tab), trim, add fade in/out, export
1080p. See `04-demo-storyboard.md` for the demo's beat sheet and annotation text.

## Consistency checklist
- [ ] Same accent teal + dark background across all four
- [ ] Same (or complementary) music bed, or one continuous track if you stitch them
- [ ] Short on-screen callouts only — no voice
- [ ] 1080p export, ~45–80s each
