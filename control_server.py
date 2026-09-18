from dotenv import load_dotenv
load_dotenv(override=True)

import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from events import broadcast, connected
from pydantic import BaseModel
import asyncio
from lead import run_lead, run_single
from repos import REPOS
from telemetry import fetch_run_events, fetch_run_metrics
from github import fetch_pr_status

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("DASHBOARD_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)

class TriggerRequest(BaseModel):
    task: str
    repo: str | None = None

@app.post("/runs")
async def trigger_run(request: TriggerRequest):
    if request.repo is not None and request.repo not in REPOS:
        raise HTTPException(status_code=400, detail=f"Unknown repo: {request.repo}")

    coro = run_single(request.repo, request.task) if request.repo else run_lead(request.task)
    task = asyncio.create_task(coro)
    task.add_done_callback(handle_run_result)
    return {"status": "started", "task": request.task, "repo": request.repo}

def handle_run_result(task: asyncio.Task):
    if task.exception():
        print(f"Run failed: {task.exception()}")

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # tylko żeby wykryć rozłączenie
    except WebSocketDisconnect:
        connected.remove(websocket)

@app.get("/repos")
def list_repos():
    return {"repos": list(REPOS.keys())}

@app.get("/runs")
async def list_run_history():
    return {"events": await fetch_run_events()}

@app.get("/runs/{run_id}/metrics")
async def get_run_metrics(run_id: str):
    return {"metrics": await fetch_run_metrics(run_id)}

@app.get("/pr-status")
async def get_pr_status(url: str):
    return {"status": await fetch_pr_status(url)}

class CompleteRunRequest(BaseModel):
    run_id: str
    repo: str

@app.post("/runs/complete")
async def complete_run(request: CompleteRunRequest):
    """User-initiated override for a run that will never finish on its own
    (e.g. the backend process died mid-run and no more events are coming -
    see the dashboard's "Mark as done" button on stale runs). Broadcasting
    a real event - rather than just tracking this client-side - means it's
    persisted via save_run_event same as any other node, survives a
    refresh, and is visible from any connected dashboard, not just the one
    that clicked the button."""
    await broadcast({
        "run_id": request.run_id,
        "repo": request.repo,
        "node": "manually_completed",
        "provider": "user",
        "status": "success",
        "detail": "Manually marked as done",
    })
    return {"status": "ok"}

class PrMergedRequest(BaseModel):
    run_id: str
    repo: str
    pr_url: str

@app.post("/runs/pr-merged")
async def record_pr_merged(request: PrMergedRequest):
    """System-detected (not user-initiated) completion signal: the dashboard
    calls this once, the first time its live GET /pr-status check for a run
    comes back "merged", so that fact gets persisted as a real RunEvent
    instead of needing to re-ask GitHub on every future page load. Without
    this, a merged-but-not-yet-recorded run flashes in the Active section on
    every refresh until the live check resolves again - this endpoint turns
    that into a one-time flash, ever, per run. Same broadcast()/save_run_event
    pipeline as every other node, so it's visible to any connected dashboard
    and survives a restart."""
    await broadcast({
        "run_id": request.run_id,
        "repo": request.repo,
        "node": "pr_merged",
        "provider": "github",
        "status": "success",
        "detail": "PR merged",
        "pr_url": request.pr_url,
    })
    return {"status": "ok"}