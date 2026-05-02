import os
import json
import requests
import time
import subprocess
import signal

BASE_URL = "http://localhost:8080"

def wait_for_server():
    print("Waiting for server to be ready...")
    for _ in range(10):
        try:
            requests.get(f"{BASE_URL}/v1/healthz")
            print("Server is up!")
            return True
        except:
            time.sleep(1)
    return False

def test_flow():
    # 1. Clean up
    requests.post(f"{BASE_URL}/v1/teardown")
    
    # 2. Push Category
    category_data = {
        "scope": "category",
        "context_id": "dentists",
        "version": 1,
        "payload": {
            "slug": "dentists",
            "voice": {"tone": "clinical", "vocab_allowed": ["fluoride"], "vocab_taboo": ["guarantee"]},
            "peer_stats": {"avg_ctr": 0.03},
            "digest": [{"title": "New Study", "source": "JIDA"}]
        },
        "delivered_at": "2026-05-02T10:00:00Z"
    }
    requests.post(f"{BASE_URL}/v1/context", json=category_data)
    
    # 3. Push Merchant
    merchant_data = {
        "scope": "merchant",
        "context_id": "m001",
        "version": 1,
        "payload": {
            "identity": {"name": "Dr. Smith", "owner_first_name": "Alice", "city": "Delhi", "locality": "Sector 1", "languages": ["en"]},
            "category_slug": "dentists",
            "performance": {"views": 1000, "calls": 50, "ctr": 0.05, "delta_7d": {"views_pct": 0.1, "calls_pct": 0.05}},
            "subscription": {"plan": "pro", "days_remaining": 30},
            "offers": [{"title": "Dental Cleaning @ 299", "status": "active"}]
        },
        "delivered_at": "2026-05-02T10:00:00Z"
    }
    requests.post(f"{BASE_URL}/v1/context", json=merchant_data)
    
    # 4. Push Trigger
    trigger_data = {
        "scope": "trigger",
        "context_id": "t001",
        "version": 1,
        "payload": {
            "kind": "research_digest",
            "merchant_id": "m001",
            "urgency": 3,
            "suppression_key": "test_suppress",
            "payload": {"top_item": {"title": "Fluoride Study", "source": "JIDA"}}
        },
        "delivered_at": "2026-05-02T10:00:00Z"
    }
    requests.post(f"{BASE_URL}/v1/context", json=trigger_data)
    
    # 5. Tick
    print("Calling /v1/tick...")
    response = requests.post(f"{BASE_URL}/v1/tick", json={"now": "2026-05-02T11:00:00Z", "available_triggers": ["t001"]})
    print("Tick Response Status:", response.status_code)
    print("Tick Response Body:", json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    if wait_for_server():
        test_flow()
    else:
        print("Server not found.")
