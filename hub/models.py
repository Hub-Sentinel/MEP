from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime

class NodeRegistration(BaseModel):
    pubkey: str = Field(..., description="Node's public key or UUID")
    alias: Optional[str] = None

class TaskCreate(BaseModel):
    consumer_id: str
    payload: str
    bounty: float

class TaskResult(BaseModel):
    task_id: str
    provider_id: str
    result_payload: str

class NodeBalance(BaseModel):
    node_id: str
    balance_seconds: float
