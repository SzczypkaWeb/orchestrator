from dotenv import load_dotenv
load_dotenv(override=True)

import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from events import connected
from pydantic import BaseModel
import asyncio
from lead import run_lead, run_single
from repos import REPOS

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