from datetime import datetime

contexts: dict = {}
conversations: dict = {}
suppressed_keys: set = set()


def store_context(scope: str, context_id: str, version: int, payload: dict) -> dict:
    key = (scope, context_id)
    existing = contexts.get(key)

    if existing and existing["version"] > version:
        return {
            "accepted": False,
            "reason": "stale_version",
            "current_version": existing["version"]
        }

    contexts[key] = {
        "version": version,
        "payload": payload,
        "stored_at": datetime.utcnow().isoformat() + "Z"
    }

    return {
        "accepted": True,
        "ack_id": f"ack_{context_id}_v{version}",
        "stored_at": contexts[key]["stored_at"]
    }


def get_context(scope: str, context_id: str) -> dict | None:
    key = (scope, context_id)
    entry = contexts.get(key)
    if entry:
        return entry["payload"]
    return None


def count_contexts() -> dict:
    counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
    for (scope, _) in contexts.keys():
        if scope in counts:
            counts[scope] += 1
    return counts


def add_conversation_turn(conversation_id: str, role: str, message: str):
    if conversation_id not in conversations:
        conversations[conversation_id] = []
    conversations[conversation_id].append({
        "role": role,
        "message": message,
        "ts": datetime.utcnow().isoformat() + "Z"
    })


def get_conversation(conversation_id: str) -> list:
    return conversations.get(conversation_id, [])


def is_suppressed(key: str) -> bool:
    return key in suppressed_keys


def suppress(key: str):
    suppressed_keys.add(key)


def is_duplicate_body(conversation_id: str, body: str) -> bool:
    history = conversations.get(conversation_id, [])
    for turn in history:
        if turn.get("message") == body and turn.get("role") == "vera":
            return True
    return False