#!/usr/bin/env python3
"""zentro-independent-core — GitHub Actions step engine.

Each workflow run takes ONE bounded step, mirroring the Cloudflare
design: if a task is queued, process the oldest one; otherwise log a
heartbeat. State lives in the repo (state/), so every run is auditable
in git history and the schedule keeps itself alive by committing.

No secrets in the repo. If the GROQ_API_KEY Actions secret is set,
ai_prompt tasks are executed against the Groq free API; otherwise the
task is completed with a recorded "skipped" result and heartbeats
continue. There is deliberately no code path for payments, purchases
or financial commitments.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "state", "tasks.json")
RUNS = os.path.join(ROOT, "state", "runs.json")
STATUS_JSON = os.path.join(ROOT, "docs", "status.json")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def save(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def run_ai(prompt):
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        return "skipped: GROQ_API_KEY not configured"
    body = json.dumps({
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": str(prompt or "")}],
    }).encode()
    req = urllib.request.Request(
        GROQ_URL, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}",
                 "User-Agent": "Mozilla/5.0 (zentro-independent-core)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return f"provider error {e.code}"
    except Exception as e:
        return f"provider error: {str(e)[:200]}"


def main():
    tasks = load(TASKS, [])
    runs = load(RUNS, [])
    queued = [t for t in tasks if t.get("status") == "queued"]
    if queued:
        task = sorted(queued, key=lambda t: t["id"])[0]
        task["status"] = "running"
        task["updated_at"] = now()
        if task.get("type") == "ai_prompt":
            result = run_ai((task.get("payload") or {}).get("prompt", ""))
        else:
            result = f"ignored: unknown task type {task.get('type')}"
        task["status"] = "done"
        task["result"] = str(result)[:4000]
        task["updated_at"] = now()
        runs.append({"at": now(), "kind": "task",
                     "detail": f"task {task['id']} ({task.get('type')}) done"})
        did = f"task {task['id']} done"
    else:
        runs.append({"at": now(), "kind": "heartbeat",
                     "detail": "alive, queue empty"})
        did = "heartbeat"
    runs = runs[-100:]
    save(TASKS, tasks)
    save(RUNS, runs)
    counts = {}
    for t in tasks:
        counts[t.get("status", "?")] = counts.get(t.get("status", "?"), 0) + 1
    save(STATUS_JSON, {
        "system": "zentro-independent-core",
        "alive": True,
        "last_run": runs[-1] if runs else None,
        "tasks": counts,
        "recent_runs": runs[-10:],
    })
    print(f"step complete: {did}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
