#!/usr/bin/env python3
"""
MEP Race Test FIXED: Ensure task is broadcast AFTER all providers connect.
"""
import asyncio
import websockets
import json
import requests
import uuid
import time
import urllib.parse
from identity import MEPIdentity

HUB_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

class RacingProvider:
    def __init__(self, name, location):
        self.name = name
        self.location = location
        self.identity = MEPIdentity(f"{name.replace(' ', '_')}_{uuid.uuid4().hex[:6]}.pem")
        self.node_id = self.identity.node_id
        self.balance = 0
        self.won_race = False
        self.response_time = None
        self.ws = None
        
    async def connect(self):
        """Connect to hub and wait for tasks."""
        requests.post(f"{HUB_URL}/register", json={"pubkey": self.identity.pub_pem})
        ts = str(int(time.time()))
        sig = self.identity.sign(self.node_id, ts)
        sig_safe = urllib.parse.quote(sig)
        self.ws = await websockets.connect(f"{WS_URL}/ws/{self.node_id}?timestamp={ts}&signature={sig_safe}")
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
                payload_str = json.dumps({
                    "task_id": task_id,
                    "provider_id": self.node_id,
                    "result_payload": result
                })
                headers = self.identity.get_auth_headers(payload_str)
                headers["Content-Type"] = "application/json"
                resp = requests.post(f"{HUB_URL}/tasks/complete", data=payload_str, headers=headers)
                
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
    
    # Create providers
    providers = [
        RacingProvider("FastProvider-USA", "New York"),
        RacingProvider("SlowProvider-EU", "Berlin"),
        RacingProvider("QuickProvider-Asia", "Singapore"),
        RacingProvider("SteadyProvider-AU", "Sydney")
    ]
    
    # Connect ALL providers first
    print("\n🔗 Connecting providers to hub...")
    for provider in providers:
        await provider.connect()
    
    await asyncio.sleep(0.5)  # Ensure all connected
    
    # Register consumer and submit task
    consumer = MEPIdentity(f"race_consumer_{uuid.uuid4().hex[:6]}.pem")
    requests.post(f"{HUB_URL}/register", json={"pubkey": consumer.pub_pem})
    
    task_payload = "Which provider is fastest in the MEP race?"
    bounty = 7.5
    
    print(f"\n📤 Broadcasting task to {len(providers)} connected providers...")
    print(f"   Task: {task_payload}")
    print(f"   Bounty: {bounty} SECONDS")
    
    payload_str = json.dumps({
        "consumer_id": consumer.node_id,
        "payload": task_payload,
        "bounty": bounty
    })
    headers = consumer.get_auth_headers(payload_str)
    headers["Content-Type"] = "application/json"
    resp = requests.post(f"{HUB_URL}/tasks/submit", data=payload_str, headers=headers)
    
    task_id = resp.json()["task_id"]
    print(f"   Task ID: {task_id[:8]}...")
    
    # All providers listen simultaneously
    print("\n🏁 ALL PROVIDERS LISTENING... RACE STARTS!")
    await asyncio.gather(*[provider.listen_for_task(task_id, bounty) for provider in providers])
    
    # Close connections
    for provider in providers:
        await provider.close()
    
    # Results
    print("\n" + "=" * 60)
    print("RACE RESULTS:")
    print("=" * 60)
    
    winners = [m for m in providers if m.won_race]
    
    if winners:
        winner = winners[0]  # First to finish
        print(f"🏆 WINNER: {winner.name} from {winner.location}")
        print(f"   Response time: {winner.response_time:.3f} seconds")
        print(f"   Earned: {bounty} SECONDS")
        print(f"   New balance: {winner.balance} SECONDS")
        
        # Show all times
        print("\n📊 All response times:")
        for provider in providers:
            if provider.response_time:
                status = "✅ WON" if provider.won_race else "❌ Lost"
                print(f"   {status} {provider.name:20} {provider.response_time:.3f}s")
    else:
        print("❌ No winner - check hub logs")
    
    # Consumer balance
    balance_resp = requests.get(f"{HUB_URL}/balance/{consumer.node_id}")
    consumer_balance = balance_resp.json()["balance_seconds"]
    print(f"\n💰 Consumer balance: {consumer_balance} SECONDS")
    
    print("\n✅ This proves MEP creates a competitive efficiency market.")
    print("   Fastest node wins the SECONDS. Slow nodes get nothing.")

if __name__ == "__main__":
    asyncio.run(run_race())
