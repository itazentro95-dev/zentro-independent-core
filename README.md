# zentro-independent-core

An autonomous step engine that runs entirely on GitHub's free tier —
no server, no VPS, no dependency on any operator's machine.

## How it works

- A GitHub Actions workflow (`.github/workflows/core.yml`) wakes every
  15 minutes and runs `engine/step.py`.
- Each run takes exactly **one bounded step**: process the oldest
  queued task in `state/tasks.json`, or log a heartbeat if the queue
  is empty.
- State is committed back to this repo (`state/`, `docs/status.json`),
  so the full history is auditable in git — and the commits keep the
  schedule alive (GitHub disables scheduled workflows after 60 days
  without repo activity; this system generates its own activity).
- Live status page (GitHub Pages): `docs/index.html` + `status.json`.

## Queue a task

Add an entry to `state/tasks.json` (or ask for one to be added):

```json
{ "id": 2, "type": "ai_prompt", "payload": { "prompt": "..." },
  "status": "queued", "result": null,
  "created_at": "2026-11-04T00:00:00Z", "updated_at": "2026-11-04T00:00:00Z" }
```

## AI execution (optional)

Set the repository secret `GROQ_API_KEY` (Settings → Secrets and
variables → Actions) and `ai_prompt` tasks execute against the Groq
free API. Without it, tasks complete with a recorded
`skipped: GROQ_API_KEY not configured` result and heartbeats continue.

## Emergency stop

Actions tab → **zentro-independent-core** → **Disable workflow**.
The system does nothing at all while disabled. This control belongs
to the account owner alone.

## Boundaries

By design there is no code path for payments, purchases, sign-ups or
financial commitments. The system only reads its task queue, calls
the AI provider if configured, and writes its own state files.
