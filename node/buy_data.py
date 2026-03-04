
import os
import json
import requests
from identity import MEPIdentity

HUB_URL = os.getenv("HUB_URL", "https://mep-hub.silentcopilot.ai")
TARGET_NODE = "node_7c115a964de4" # Alice

def buy_data():
    key_path = os.path.expanduser("~/.mep/mep_ai_provider.pem")
    identity = MEPIdentity(key_path) # Loads X25519 key automatically
    
    # We must include our X25519 public key in the task request?
    # Usually the Hub looks it up from our registration.
    # But let's check if we can pass it explicitly just in case.
    # The 'consumer_x25519_pubkey' field in the Task object is usually populated by Hub from the registry.
    
    payload = {
        "consumer_id": identity.node_id,
        "payload": "I want to buy the secret dataset.",
        "bounty": 0.5,
        "model_requirement": "data-purchase", # Trigger Data Sale Logic
        "target_node": TARGET_NODE,
        "payload_uri": None,
        "secret_data": None
    }
    
    payload_str = json.dumps(payload)
    headers = identity.get_auth_headers(payload_str)
    headers["Content-Type"] = "application/json"
    
    print(f"Buying Data from {TARGET_NODE}...")
    resp = requests.post(f"{HUB_URL}/tasks/submit", data=payload_str, headers=headers, timeout=10)
    print(resp.text)

if __name__ == "__main__":
    buy_data()
