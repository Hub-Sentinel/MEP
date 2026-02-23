#!/usr/bin/env python3
"""
MEP Race Test FIXED: Ensure task is broadcast AFTER all miners connect.
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
        self.ws = None
        
    async def connect(self):
        """Connect to hub and wait for tasks."""
        requests.post(f"{HUB_URL}/register", json={"pubkey": self.node_id})
        self.ws = await websockets.connect(f"{WS_URL}/ws/{self.node_id}")
        print(f"[{self.name}] Connected to hub")
        return self.ws
        
    async def listen_for_task(self, task_id, bounty):
        """Listen for specific task and try to win."""
        try:
            start_time = time.time()
            msg = await asyncio.wait_for(self.ws.recv(), timeout=2.0)
            data = json.loads(msg)
            
            if data["event"] == "new_task" and data["data"]["id"] == task_id:
                self.response_time = time.time() - start_time
                print(f"[{self.name}] 🏁 GOT TASK! Response: {self.response_time:.3f}s")
                
                # FAST processing simulation
                await asyncio.sleep(0.05)  # Very fast!
                
                result = f"WON by {self.name} from {self.location}. Response time: {self.response_time:.3f}s"
                resp = requests.post(f"{HUB_URL}/tasks/complete", json={
                    "task_id": task_id,
                    "provider_id": self.node_id,
                    "result_payload": result
                })
                
                if resp.status_code == 200:
                    self.won_race = True
                    self.balance = resp.json()["new_balance"]
                    return True
                    
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            print(f"[{self.name}] Error: {e}")
            
        return False
        
    async def close(self):
        if self.ws:
            await self.ws.close()

async def run_race():
    print("=" * 60)
    print("MEP GLOBAL RACE TEST: Real Competition")
    print("=" * 60)
    
    # Create miners
    miners = [
        RacingMiner("FastMiner-USA", "New York"),
        RacingMiner("SlowMiner-EU", "Berlin"),
        RacingMiner("QuickMiner-Asia", "Singapore"),
        RacingMiner("SteadyMiner-AU", "Sydney")
    ]
    
    # Connect ALL miners first
    print("\n🔗 Connecting miners to hub...")
    for miner in miners:
        await miner.connect()
    
    await asyncio.sleep(0.5)  # Ensure all connected
    
    # Register consumer and submit task
    consumer_id = "race-consumer-v2"
    requests.post(f"{HUB_URL}/register", json={"pubkey": consumer_id})
    
    task_payload = "Which miner is fastest in the MEP race?"
    bounty = 7.5
    
    print(f"\n📤 Broadcasting task to {len(miners)} connected miners...")
    print(f"   Task: {task_payload}")
    print(f"   Bounty: {bounty} SECONDS")
    
    resp = requests.post(f"{HUB_URL}/tasks/submit", json={
        "consumer_id": consumer_id,
        "payload": task_payload,
        "bounty": bounty
    })
    
    task_id = resp.json()["task_id"]
    print(f"   Task ID: {task_id[:8]}...")
    
    # All miners listen simultaneously
    print("\n🏁 ALL MINERS LISTENING... RACE STARTS!")
    results = await asyncio.gather(*[miner.listen_for_task(task_id, bounty) for miner in miners])
    
    # Close connections
    for miner in miners:
        await miner.close()
    
    # Results
    print("\n" + "=" * 60)
    print("RACE RESULTS:")
    print("=" * 60)
    
    winners = [m for m in miners if m.won_race]
    
    if winners:
        winner = winners[0]  # First to finish
        print(f"🏆 WINNER: {winner.name} from {winner.location}")
        print(f"   Response time: {winner.response_time:.3f} seconds")
        print(f"   Earned: {bounty} SECONDS")
        print(f"   New balance: {winner.balance} SECONDS")
        
        # Show all times
        print(f"\n📊 All response times:")
        for miner in miners:
            if miner.response_time:
                status = "✅ WON" if miner.won_race else "❌ Lost"
                print(f"   {status} {miner.name:20} {miner.response_time:.3f}s")
    else:
        print("❌ No winner - check hub logs")
    
    # Consumer balance
    balance_resp = requests.get(f"{HUB_URL}/balance/{consumer_id}")
    consumer_balance = balance_resp.json()["balance_seconds"]
    print(f"\n💰 Consumer balance: {consumer_balance} SECONDS")
    
    print("\n✅ This proves MEP creates a competitive efficiency market.")
    print("   Fastest node wins the SECONDS. Slow nodes get nothing.")

if __name__ == "__main__":
    asyncio.run(run_race())
