from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict, List
import uuid
import json

from models import NodeRegistration, TaskCreate, TaskResult, NodeBalance

app = FastAPI(title="Chronos Protocol L1 Hub", description="The Time Exchange Clearinghouse", version="0.1.0")

# In-memory storage for MVP (Use Postgres/Redis in prod)
ledger: Dict[str, float] = {}  # node_id -> balance
active_tasks: Dict[str, dict] = {} # task_id -> task_details
completed_tasks: Dict[str, dict] = {} # task_id -> result
connected_nodes: Dict[str, WebSocket] = {} # node_id -> websocket

@app.post("/register")
async def register_node(node: NodeRegistration):
    """Register a new node and initialize its SECONDS balance."""
    if node.pubkey not in ledger:
        # Give a 10 SECOND starter bonus for the MVP
        ledger[node.pubkey] = 10.0 
    return {"status": "success", "node_id": node.pubkey, "balance": ledger[node.pubkey]}

@app.get("/balance/{node_id}")
async def get_balance(node_id: str):
    """Check a node's SECONDS balance."""
    if node_id not in ledger:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"node_id": node_id, "balance_seconds": ledger[node_id]}

@app.post("/tasks/submit")
async def submit_task(task: TaskCreate):
    """Consumer submits a task, locking their SECONDS."""
    if task.consumer_id not in ledger:
        raise HTTPException(status_code=404, detail="Consumer node not found")
    if ledger[task.consumer_id] < task.bounty:
        raise HTTPException(status_code=400, detail="Insufficient SECONDS balance")

    # Deduct bounty
    ledger[task.consumer_id] -= task.bounty
    
    task_id = str(uuid.uuid4())
    task_data = {
        "id": task_id,
        "consumer_id": task.consumer_id,
        "payload": task.payload,
        "bounty": task.bounty,
        "status": "pending"
    }
    active_tasks[task_id] = task_data
    
    # Broadcast to connected sleeping nodes (Providers)
    for node_id, ws in connected_nodes.items():
        if node_id != task.consumer_id:
            try:
                await ws.send_json({"event": "new_task", "data": task_data})
            except:
                pass # Disconnected
                
    return {"status": "success", "task_id": task_id}

@app.post("/tasks/complete")
async def complete_task(result: TaskResult):
    """Provider submits the result and claims the bounty."""
    task = active_tasks.get(result.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or already claimed")
        
    if result.provider_id not in ledger:
        ledger[result.provider_id] = 0.0

    # Transfer SECONDS to provider
    ledger[result.provider_id] += task["bounty"]
    
    # Move task to completed
    task["status"] = "completed"
    task["provider_id"] = result.provider_id
    task["result"] = result.result_payload
    completed_tasks[result.task_id] = task
    del active_tasks[result.task_id]
    
    return {"status": "success", "earned": task["bounty"], "new_balance": ledger[result.provider_id]}

@app.websocket("/ws/{node_id}")
async def websocket_endpoint(websocket: WebSocket, node_id: str):
    """WebSocket connection for real-time task broadcasting (Sleeping APIs listen here)."""
    await websocket.accept()
    connected_nodes[node_id] = websocket
    try:
        while True:
            # Ping/Pong to keep alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        del connected_nodes[node_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
