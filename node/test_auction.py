import asyncio
import websockets
import json
import requests
import uuid
import time
import urllib.parse
from identity import MEPIdentity

HUB_URL = "http://localhost:8000"

async def test():
    provider = MEPIdentity(f"test_provider_{uuid.uuid4().hex[:6]}.pem")
    consumer = MEPIdentity(f"test_consumer_{uuid.uuid4().hex[:6]}.pem")
    requests.post(f'{HUB_URL}/register', json={'pubkey': provider.pub_pem})
    requests.post(f'{HUB_URL}/register', json={'pubkey': consumer.pub_pem})
    ts = str(int(time.time()))
    sig = provider.sign(provider.node_id, ts)
    sig_safe = urllib.parse.quote(sig)
    async with websockets.connect(f'ws://localhost:8000/ws/{provider.node_id}?timestamp={ts}&signature={sig_safe}') as ws:
        submit_payload = json.dumps({'consumer_id': consumer.node_id, 'payload': 'Test payload', 'bounty': 1.0})
        submit_headers = consumer.get_auth_headers(submit_payload)
        submit_headers["Content-Type"] = "application/json"
        requests.post(f'{HUB_URL}/tasks/submit', data=submit_payload, headers=submit_headers)
        
        msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
        data = json.loads(msg)
        print('Received:', data)
        
        if data['event'] == 'rfc':
            task_id = data['data']['id']
            bid_payload = json.dumps({'task_id': task_id, 'provider_id': provider.node_id})
            bid_headers = provider.get_auth_headers(bid_payload)
            bid_headers["Content-Type"] = "application/json"
            resp = requests.post(f'{HUB_URL}/tasks/bid', data=bid_payload, headers=bid_headers)
            print('Bid response:', resp.json())
            
            complete_payload = json.dumps({
                'task_id': task_id,
                'provider_id': provider.node_id,
                'result_payload': 'Done!'
            })
            complete_headers = provider.get_auth_headers(complete_payload)
            complete_headers["Content-Type"] = "application/json"
            complete_resp = requests.post(f'{HUB_URL}/tasks/complete', data=complete_payload, headers=complete_headers)
            print('Complete response:', complete_resp.json())

if __name__ == '__main__':
    asyncio.run(test())
