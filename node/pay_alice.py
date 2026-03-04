
import os
import sys
import json
import requests
from identity import MEPIdentity

HUB_URL = os.getenv("HUB_URL", "https://mep-hub.silentcopilot.ai")
TARGET_NODE = "node_7c115a964de4" # Alice

def pay_alice():
    # Use my primary key
    key_path = os.path.expanduser("~/.mep/mep_ai_provider.pem")
    identity = MEPIdentity(key_path)
    
    payload = {
        "consumer_id": identity.node_id,
        "payload": "Hello Alice! Please compute this for 0.5 SECONDS.",
        "bounty": 0.5,
        "model_requirement": "gemini-1.5-flash", # Simple task
        "target_node": TARGET_NODE,
        "payload_uri": None,
        "secret_data": None
    }
    
    payload_str = json.dumps(payload)
    headers = identity.get_auth_headers(payload_str)
    headers["Content-Type"] = "application/json"
    
    print(f"Sending 0.5 SECONDS to {TARGET_NODE}...")
    resp = requests.post(f"{HUB_URL}/tasks/submit", data=payload_str, headers=headers, timeout=10)
    print(resp.text)

if __name__ == "__main__":
    pay_alice()
