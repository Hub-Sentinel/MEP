#!/usr/bin/env python3
"""
MEP Race Test: Multiple providers compete for the same task.
Simulates a global network of sleeping nodes.
"""
import asyncio
import websockets
import json
import requests
import uuid
import time

HUB_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

class RacingMiner:
    def __init__(self, name, location):
        self.name = name
        self.location = location
        self.node_id = f"{name}-{uuid.uuid4().hex[:6]}"
        self.balance = 0
        self.won_race = False
        self.response_time = None
        
    async def compete(self, task_id, task_payload, bounty):
        """Connect and try to win the task."""
        print(f"[{self.name} in {self.location}] Connecting to MEP Hub...")
        
        # Register
        requests.post(f"{HUB_URL}/register", json={"pubkey": self.node_id})
        
        # Connect via WebSocket
        start_time = time.time()
        async with websockets.connect(f"{WS_URL}/ws/{self.node_id}") as ws:
            print(f"[{self.name}] Connected. Waiting for task {task_id[:8]}...")
            
            try:
                # Listen for the task
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(msg)
                
                if data["event"] == "new_task" and data["data"]["id"] == task_id:
                    self.response_time = time.time() - start_time
                    print(f"[{self.name}] 🏁 GOT THE TASK! Response: {self.response_time:.3f}s")
                    
                    # Simulate processing (faster miners win)
                    process_time = 0.1 if "fast" in self.name.lower() else 0.5
                    await asyncio.sleep(process_time)
                    
                    # Submit result
                    result = f"Processed by {self.name} from {self.location}. Task: {task_payload[:30]}..."
                    resp = requests.post(f"{HUB_URL}/tasks/complete", json={
                        "task_id": task_id,
                        "provider_id": self.node_id,
                        "result_payload": result
                    })
                    
                    if resp.status_code == 200:
                        self.won_race = True
                        self.balance = resp.json()["new_balance"]
                        print(f"[{self.name}] 🎉 WON THE RACE! Earned {bounty} SECONDS")
                    else:
                        print(f"[{self.name}] ❌ Race lost (someone else finished first)")
                        
            except asyncio.TimeoutError:
                print(f"[{self.name}] Timeout - task already taken")
            except Exception as e:
                print(f"[{self.name}] Error: {e}")

async def run_race():
    print("=" * 60)
    print("MEP GLOBAL RACE TEST: Multiple Nodes Compete for One Task")
    print("=" * 60)
    
    # Register consumer
    consumer_id = "race-test-consumer"
    requests.post(f"{HUB_URL}/register", json={"pubkey": consumer_id})
    
    # Create 4 miners in different "locations"
    miners = [
        RacingMiner("FastMiner-USA", "New York"),
        RacingMiner("SlowMiner-EU", "Berlin"),
        RacingMiner("QuickMiner-Asia", "Singapore"),
        RacingMiner("SteadyMiner-AU", "Sydney")
    ]
    
    # Submit a task
    task_payload = "Analyze the MEP race dynamics and provide insights"
    bounty = 8.5
    
    print(f"\n📤 Submitting task: {task_payload[:50]}...")
    print(f"   Bounty: {bounty} SECONDS")
    
    resp = requests.post(f"{HUB_URL}/tasks/submit", json={
        "consumer_id": consumer_id,
        "payload": task_payload,
        "bounty": bounty
    })
    
    task_data = resp.json()
    task_id = task_data["task_id"]
    print(f"   Task ID: {task_id[:8]}...")
    
    # Start all miners simultaneously
    print("\n🏁 Starting miners...")
    tasks = [miner.compete(task_id, task_payload, bounty) for miner in miners]
    await asyncio.gather(*tasks)
    
    # Results
    print("\n" + "=" * 60)
    print("RACE RESULTS:")
    print("=" * 60)
    
    winner = None
    for miner in miners:
        status = "🏆 WINNER" if miner.won_race else "❌ Lost"
        time_str = f"{miner.response_time:.3f}s" if miner.response_time else "N/A"
        print(f"{status} {miner.name:20} {miner.location:15} Response: {time_str:8} Balance: {miner.balance}")
        
        if miner.won_race:
            winner = miner
    
    if winner:
        print(f"\n🎯 The market chose: {winner.name} from {winner.location}")
        print(f"   Reason: Fastest response time ({winner.response_time:.3f}s)")
        print(f"   Economics: Earned {bounty} SECONDS for being efficient")
    else:
        print("\n⚠️ No winner - task may have failed")
    
    # Check consumer balance
    balance_resp = requests.get(f"{HUB_URL}/balance/{consumer_id}")
    consumer_balance = balance_resp.json()["balance_seconds"]
    print(f"\n💰 Consumer spent {bounty} SECONDS, new balance: {consumer_balance}")
    
    print("\n✅ Race test complete. This simulates how MEP creates a")
    print("   global efficiency market: fastest nodes win SECONDS.")

if __name__ == "__main__":
    asyncio.run(run_race())
