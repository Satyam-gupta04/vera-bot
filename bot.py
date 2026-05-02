import time
import uuid
import json
import threading
from datetime import datetime
from fastapi import FastAPI, Response
from pydantic import BaseModel
from typing import Any



from store import (
    store_context,
    get_context,
    count_contexts,
    add_conversation_turn,
    is_suppressed,
    suppress,
    is_duplicate_body
)
from composer import compose
from reply_handler import handle_reply
from loader import load_all_data

app = FastAPI()
START_TIME = time.time()

load_all_data()

VALID_SCOPES = {"category", "merchant", "customer", "trigger"}


class ContextBody(BaseModel):
    scope: str
    context_id: str
    version: int
    payload: dict[str, Any]
    delivered_at: str


class TickBody(BaseModel):
    now: str
    available_triggers: list[str] = []


class ReplyBody(BaseModel):
    conversation_id: str
    merchant_id: str | None = None
    customer_id: str | None = None
    from_role: str
    message: str
    received_at: str
    turn_number: int


@app.get("/v1/healthz")
async def healthz():
    counts = count_contexts()
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "contexts_loaded": counts
    }


@app.get("/v1/metadata")
async def metadata():
    return {
        "team_name": "Satyam Gupta",
        "team_members": ["Satyam Gupta"],
        "model": "claude-sonnet-4-5",
        "approach": "4-context composer with trigger routing, auto-reply detection, customer reply branching, and 10 gold-standard few-shot examples",
        "contact_email": "your-real-email@gmail.com",
        "version": "2.0.0",
        "submitted_at": datetime.utcnow().isoformat() + "Z"
    }


@app.post("/v1/context")
async def push_context(body: ContextBody):
    if body.scope not in VALID_SCOPES:
        return Response(
            content=json.dumps({
                "accepted": False,
                "reason": "invalid_scope",
                "details": f"scope must be one of {list(VALID_SCOPES)}"
            }),
            status_code=400,
            media_type="application/json"
        )
    result = store_context(
        scope=body.scope,
        context_id=body.context_id,
        version=body.version,
        payload=body.payload
    )
    if not result["accepted"]:
        return Response(
            content=json.dumps(result),
            status_code=409,
            media_type="application/json"
        )
    return result


@app.post("/v1/tick")
async def tick(body: TickBody):
    actions = []
    print(f"\n[TICK] now={body.now} triggers={body.available_triggers}")
    print(f"[TICK] contexts in store: {count_contexts()}")

    for trigger_id in body.available_triggers:
        print(f"\n[TICK] processing trigger: {trigger_id}")

        trigger = get_context("trigger", trigger_id)
        if not trigger:
            print(f"[TICK] trigger not found in store: {trigger_id}")
            continue
        print(f"[TICK] trigger found: kind={trigger.get('kind')}")

        merchant_id = trigger.get("merchant_id")
        if not merchant_id:
            print(f"[TICK] no merchant_id in trigger")
            continue
        print(f"[TICK] merchant_id={merchant_id}")

        merchant = get_context("merchant", merchant_id)
        if not merchant:
            print(f"[TICK] merchant not found: {merchant_id}")
            print(f"[TICK] available merchants: {[k for (s,k) in __import__('store').contexts.keys() if s=='merchant'][:5]}")
            continue
        print(f"[TICK] merchant found: {merchant.get('identity',{}).get('name','?')}")

        category_slug = merchant.get("category_slug", "")
        print(f"[TICK] category_slug={category_slug}")

        category = get_context("category", category_slug)
        if not category:
            print(f"[TICK] category not found: {category_slug}")
            print(f"[TICK] available categories: {[k for (s,k) in __import__('store').contexts.keys() if s=='category']}")
            from store import contexts
            for (scope, cid), entry in contexts.items():
                if scope == "category":
                    category = entry["payload"]
                    print(f"[TICK] using fallback category: {cid}")
                    break
        if not category:
            print(f"[TICK] no category at all — skipping")
            continue
        print(f"[TICK] category found")

        customer = None
        customer_id = trigger.get("customer_id")
        if customer_id:
            customer = get_context("customer", customer_id)
            print(f"[TICK] customer_id={customer_id}, found={customer is not None}")

        suppression_key = trigger.get("suppression_key", "")
        if suppression_key and is_suppressed(suppression_key):
            print(f"[TICK] suppressed: {suppression_key}")
            continue

        try:
            print(f"[TICK] composing message...")
            composed = compose(
                category=category,
                merchant=merchant,
                trigger=trigger,
                customer=customer
            )
            print(f"[TICK] composed body length: {len(composed.get('body',''))}")
        except Exception as e:
            print(f"[TICK] compose error: {e}")
            continue

        if not composed.get("body"):
            print(f"[TICK] empty body after compose")
            continue

        conversation_id = f"conv_{merchant_id}_{trigger_id}_{uuid.uuid4().hex[:8]}"

        if is_duplicate_body(conversation_id, composed["body"]):
            print(f"[TICK] duplicate body")
            continue

        add_conversation_turn(conversation_id, "vera", composed["body"])

        if suppression_key:
            suppress(suppression_key)

        trigger_kind = trigger.get("kind", "generic")

        action = {
            "conversation_id": conversation_id,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "send_as": composed.get("send_as", "vera"),
            "trigger_id": trigger_id,
            "template_name": f"vera_{trigger_kind}_v1",
            "template_params": [
                merchant.get("identity", {}).get("owner_first_name", ""),
                composed["body"][:100],
                composed.get("cta", "")
            ],
            "body": composed["body"],
            "cta": composed.get("cta", "open_ended"),
            "suppression_key": composed.get("suppression_key", suppression_key),
            "rationale": composed.get("rationale", "")
        }

        actions.append(action)
        print(f"[TICK] action added for {merchant_id}")

        if len(actions) >= 20:
            break

    print(f"[TICK] returning {len(actions)} actions")
    return {"actions": actions}


@app.post("/v1/reply")
async def reply(body: ReplyBody):
    add_conversation_turn(
        body.conversation_id,
        body.from_role,
        body.message
    )

    result = handle_reply(
        conversation_id=body.conversation_id,
        merchant_id=body.merchant_id or "",
        customer_id=body.customer_id,
        message=body.message,
        turn_number=body.turn_number,
        from_role=body.from_role
    )
    return result


@app.post("/v1/teardown")
async def teardown():
    from store import contexts, conversations, suppressed_keys
    contexts.clear()
    conversations.clear()
    suppressed_keys.clear()
    return {
        "status": "wiped",
        "ts": datetime.utcnow().isoformat() + "Z"
    }


def keep_alive():
    import urllib.request
    while True:
        try:
            urllib.request.urlopen(
                "https://vera-bot-reg3.onrender.com/v1/healthz",
                timeout=10
            )
        except:
            pass
        time.sleep(840)


threading.Thread(target=keep_alive, daemon=True).start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)