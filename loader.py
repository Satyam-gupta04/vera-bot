import json
import os
from store import store_context

def load_all_data(expanded_dir: str = "expanded"):
    print("Dataset loading skipped — waiting for judge to push context")

    categories_dir = os.path.join(expanded_dir, "categories")
    if os.path.exists(categories_dir):
        for filename in os.listdir(categories_dir):
            if filename.endswith(".json"):
                with open(os.path.join(categories_dir, filename)) as f:
                    payload = json.load(f)
                slug = payload.get("slug", filename.replace(".json", ""))
                store_context("category", slug, 0, payload)
        print("  Categories loaded")

    merchants_dir = os.path.join(expanded_dir, "merchants")
    if os.path.exists(merchants_dir):
        count = 0
        for filename in os.listdir(merchants_dir):
            if filename.endswith(".json"):
                with open(os.path.join(merchants_dir, filename)) as f:
                    payload = json.load(f)
                merchant_id = payload.get("merchant_id", filename.replace(".json", ""))
                store_context("merchant", merchant_id, 0, payload)
                count += 1
        print(f"  {count} merchants loaded")

    customers_dir = os.path.join(expanded_dir, "customers")
    if os.path.exists(customers_dir):
        count = 0
        for filename in os.listdir(customers_dir):
            if filename.endswith(".json"):
                with open(os.path.join(customers_dir, filename)) as f:
                    payload = json.load(f)
                customer_id = payload.get("customer_id", filename.replace(".json", ""))
                store_context("customer", customer_id, 0, payload)
                count += 1
        print(f"  {count} customers loaded")

    triggers_dir = os.path.join(expanded_dir, "triggers")
    if os.path.exists(triggers_dir):
        count = 0
        for filename in os.listdir(triggers_dir):
            if filename.endswith(".json"):
                with open(os.path.join(triggers_dir, filename)) as f:
                    payload = json.load(f)
                trigger_id = payload.get("id", filename.replace(".json", ""))
                store_context("trigger", trigger_id, 0, payload)
                count += 1
        print(f"  {count} triggers loaded")

    print("Dataset ready")