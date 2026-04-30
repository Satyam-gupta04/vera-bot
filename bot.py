import time
import uuid
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any

from loader import load_all_data

from store import (
    store_context,
    get_context,
    count_contexts,
    add_conversation_turn,
    is_suppressed,
    suppress
)
from composer import compose
from reply_handler import handle_reply


load_all_data()

app = FastAPI()
START_TIME = time.time()


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
        "model": "claude-sonnet-4-20250514",
        "approach": "4-context composer with trigger routing, auto-reply detection, and intent transition handling",
        "contact_email": "your-real-email@gmail.com",
        "version": "1.0.0",
        "submitted_at": datetime.utcnow().isoformat() + "Z"
    }


@app.post("/v1/context")
async def push_context(body: ContextBody):

    result = store_context(
        scope=body.scope,
        context_id=body.context_id,
        version=body.version,
        payload=body.payload
    )
    return result


@app.post("/v1/tick")
async def tick(body: TickBody):

    actions = []

    for trigger_id in body.available_triggers:


        trigger = get_context("trigger", trigger_id)
        if not trigger:
            continue


        expires_at = trigger.get("expires_at", "")
        if expires_at and expires_at < body.now:
            continue


        suppression_key = trigger.get("suppression_key", "")
        if suppression_key and is_suppressed(suppression_key):
            continue


        merchant_id = trigger.get("merchant_id")
        if not merchant_id:
            continue

        merchant = get_context("merchant", merchant_id)
        if not merchant:
            continue


        category_slug = merchant.get("category_slug", "")
        category = get_context("category", category_slug)
        if not category:
            continue


        customer = None
        customer_id = trigger.get("customer_id")
        if customer_id:
            customer = get_context("customer", customer_id)


        try:
            composed = compose(
                category=category,
                merchant=merchant,
                trigger=trigger,
                customer=customer
            )
        except Exception as e:
            continue


        if not composed.get("body"):
            continue


        conversation_id = f"conv_{merchant_id}_{trigger_id}_{uuid.uuid4().hex[:8]}"


        add_conversation_turn(conversation_id, "vera", composed["body"])


        if suppression_key:
            suppress(suppression_key)


        trigger_kind = trigger.get("kind", "generic")
        template_name = f"vera_{trigger_kind}_v1"


        action = {
            "conversation_id": conversation_id,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "send_as": composed.get("send_as", "vera"),
            "trigger_id": trigger_id,
            "template_name": template_name,
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


        if len(actions) >= 20:
            break

    return {"actions": actions}


@app.post("/v1/reply")
async def reply(body: ReplyBody):
    """
    Judge sends merchant's reply here.
    Bot must respond within 30 seconds.
    Returns: send, wait, or end action.
    """


    add_conversation_turn(
        body.conversation_id,
        "merchant",
        body.message
    )

    
    result = handle_reply(
        conversation_id=body.conversation_id,
        merchant_id=body.merchant_id or "",
        customer_id=body.customer_id,
        message=body.message,
        turn_number=body.turn_number
    )

    return result

import threading

def keep_alive():
    import time
    import urllib.request
    while True:
        try:
            urllib.request.urlopen(
                "https://vera-bot-reg3.onrender.com/v1/healthz",
                timeout=10
            )
        except:
            pass
        time.sleep(840)  # ping every 14 minutes

threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)