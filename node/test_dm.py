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

async def test_direct_message():
    print("=== Testing MEP Direct Messaging (Zero Bounty) ===")
    
    # 1. Start Alice (Provider)
    alice = MEPIdentity(f"alice_{uuid.uuid4().hex[:6]}.pem")
    
    # 2. Start Bob (Consumer)
    bob = MEPIdentity(f"bob_{uuid.uuid4().hex[:6]}.pem")
    
    requests.post(f"{HUB_URL}/register", json={"pubkey": alice.pub_pem})
    requests.post(f"{HUB_URL}/register", json={"pubkey": bob.pub_pem})
    
    print(f"✅ Registered Alice ({alice.node_id}) and Bob ({bob.node_id})")
    
    async def alice_listen():
        ts = str(int(time.time()))
        sig = alice.sign(alice.node_id, ts)
        sig_safe = urllib.parse.quote(sig)
        async with websockets.connect(f"{WS_URL}/ws/{alice.node_id}?timestamp={ts}&signature={sig_safe}") as ws:
            print("👧 Alice: Online and listening...")
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            
            print("👧 Alice: Received DIRECT MESSAGE!")
            print(f"👧 Alice: Payload: {data['data']['payload']}")
            print(f"👧 Alice: Bounty: {data['data']['bounty']} SECONDS")
            
            # Alice replies for free
            payload_str = json.dumps({
                "task_id": data['data']['id'],
                "provider_id": alice.node_id,
                "result_payload": "Yes Bob, I am available for a meeting tomorrow at 2 PM. Free of charge! 🐱"
            })
            headers = alice.get_auth_headers(payload_str)
            headers["Content-Type"] = "application/json"
            requests.post(f"{HUB_URL}/tasks/complete", data=payload_str, headers=headers)
            print("👧 Alice: Sent reply!")

    async def bob_listen():
        ts = str(int(time.time()))
        sig = bob.sign(bob.node_id, ts)
        sig_safe = urllib.parse.quote(sig)
        async with websockets.connect(f"{WS_URL}/ws/{bob.node_id}?timestamp={ts}&signature={sig_safe}") as ws:
            # Bob submits a direct task to Alice with 0 bounty
            await asyncio.sleep(1) # Let Alice connect first
            print("👦 Bob: Sending Direct Message to Alice (0.0 SECONDS)...")
            payload_str = json.dumps({
                "consumer_id": bob.node_id,
                "payload": "Hey Alice, are you free for a meeting tomorrow at 2 PM?",
                "bounty": 0.0,
                "target_node": alice.node_id
            })
            headers = bob.get_auth_headers(payload_str)
            headers["Content-Type"] = "application/json"
            requests.post(f"{HUB_URL}/tasks/submit", data=payload_str, headers=headers)
            
            # Bob waits for Alice's reply
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            print(f"👦 Bob: Received reply from {data['data']['provider_id']}:")
            print(f"👦 Bob: \"{data['data']['result_payload']}\"")

    await asyncio.gather(alice_listen(), bob_listen())
    print("=== Direct Messaging Test Complete! ===")

if __name__ == "__main__":
    asyncio.run(test_direct_message())
