from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
import asyncio
import json
from lead import run_lead

app = FastAPI()

class TriggerRequest(BaseModel):
    task: str

@app.post("/runs")
async def trigger_run(request: TriggerRequest):
    task = asyncio.create_task(run_lead(request.task))
    task.add_done_callback(handle_run_result)
    return {"status": "started", "task": request.task}

def handle_run_result(task: asyncio.Task):
    if task.exception():
        print(f"Run failed: {task.exception()}")

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    counter = 0
    while True:
        await websocket.send_text(json.dumps({"counter": counter}))
        counter += 1
        await asyncio.sleep(1)