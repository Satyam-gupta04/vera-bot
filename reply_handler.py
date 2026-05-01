import json
import anthropic
import os
from dotenv import load_dotenv
from store import get_conversation, add_conversation_turn, get_context

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

AUTO_REPLY_PATTERNS = [
    "thank you for contacting",
    "thanks for contacting",
    "we will get back to you",
    "we'll get back to you",
    "our team will respond",
    "automated message",
    "auto reply",
    "autoreply",
    "this is an automated",
    "i am currently unavailable",
    "i'm currently unavailable",
    "out of office",
]

INTENT_PHRASES = [
    "let's do it", "lets do it", "ok do it", "yes do it",
    "go ahead", "please go ahead", "haan karo", "kar do",
    "chaliye", "chalo karte hain", "yes please", "yes, please",
    "sounds good", "ok proceed", "proceed", "confirm",
]

STOP_PHRASES = [
    "stop", "not interested", "no thanks", "no thank you",
    "leave me alone", "don't message", "dont message",
    "unsubscribe", "band karo", "mat bhejo", "nahi chahiye",
    "boring", "useless", "waste of time", "stop messaging",
]

OFF_TOPIC_PHRASES = [
    "gst", "income tax", "filing", "loan", "insurance",
    "legal", "court", "police", "help me with", "can you also",
]

HOSTILE_PHRASES = [
    "idiot", "stupid", "useless bot", "worst",
    "bakwas", "bekar",
]


def is_auto_reply(message: str) -> bool:
    message_lower = message.lower().strip()
    for pattern in AUTO_REPLY_PATTERNS:
        if pattern in message_lower:
            return True
    return False


def is_intent_transition(message: str) -> bool:
    message_lower = message.lower().strip()
    for phrase in INTENT_PHRASES:
        if phrase in message_lower:
            return True
    return False


def is_hard_stop(message: str) -> bool:
    message_lower = message.lower().strip()
    for phrase in STOP_PHRASES:
        if phrase in message_lower:
            return True
    return False


def count_auto_replies(conversation: list) -> int:
    count = 0
    for turn in reversed(conversation):
        if turn["role"] == "merchant" and is_auto_reply(turn["message"]):
            count += 1
        elif turn["role"] == "merchant":
            break
    return count


def handle_reply(
    conversation_id: str,
    merchant_id: str,
    customer_id: str | None,
    message: str,
    turn_number: int,
    from_role: str = "merchant"
) -> dict:

    add_conversation_turn(conversation_id, from_role, message)
    conversation = get_conversation(conversation_id)

    if is_hard_stop(message):
        return {
            "action": "end",
            "rationale": "Opted out. Closing conversation."
        }

    message_lower = message.lower()

    if any(phrase in message_lower for phrase in HOSTILE_PHRASES):
        return {
            "action": "send",
            "body": "Samajh sakta hoon — agar kabhi listing ya campaigns pe kaam karna ho toh batayein. 🙏",
            "cta": "none",
            "rationale": "Hostile message. Responded politely."
        }

    if any(phrase in message_lower for phrase in OFF_TOPIC_PHRASES):
        return {
            "action": "send",
            "body": "GST/legal matters meri expertise nahi hai — uske liye CA se baat karein. Main aapki magicpin listing aur customers ke liye yahan hoon.",
            "cta": "open_ended",
            "rationale": "Off-topic. Redirected."
        }

    # Customer reply — handle separately
    if from_role == "customer":
        return handle_customer_reply(
            conversation_id, merchant_id, customer_id, message, conversation
        )

    # Merchant reply below
    if is_auto_reply(message):
        auto_reply_count = count_auto_replies(conversation)
        if auto_reply_count == 1:
            return {
                "action": "send",
                "body": "Looks like an automated reply 😊 When you get a chance, just reply YES to continue.",
                "cta": "binary_yes_no",
                "rationale": "First auto-reply. Sending gentle nudge."
            }
        elif auto_reply_count == 2:
            return {
                "action": "wait",
                "wait_seconds": 14400,
                "rationale": "Second auto-reply. Backing off 4 hours."
            }
        else:
            return {
                "action": "end",
                "rationale": "Auto-reply 3+ times. Closing."
            }

    if is_intent_transition(message):
        merchant = get_context("merchant", merchant_id)
        if merchant:
            offers = merchant.get("offers", [])
            active_offers = [o for o in offers if o.get("status") == "active"]
            offer_title = active_offers[0].get("title", "") if active_offers else ""
            owner_name = merchant.get("identity", {}).get("owner_first_name", "")
            total_customers = merchant.get("customer_aggregate", {}).get("total_unique_ytd", 0)

            action_body = f"Perfect{', ' + owner_name if owner_name else ''}! Setting it up now."
            if offer_title and total_customers:
                action_body += f" I'll draft the campaign with your '{offer_title}' offer for your {total_customers} customers. Reply CONFIRM to send."
            else:
                action_body += " What would you like to tackle first — profile update, campaign, or customer outreach?"

            add_conversation_turn(conversation_id, "vera", action_body)
            return {
                "action": "send",
                "body": action_body,
                "cta": "binary_confirm_cancel",
                "rationale": "Intent transition. Switching to action mode."
            }

    return compose_reply_with_claude(
        conversation_id, merchant_id, customer_id, message, conversation
    )


def handle_customer_reply(
    conversation_id: str,
    merchant_id: str,
    customer_id: str | None,
    message: str,
    conversation: list
) -> dict:
    customer = get_context("customer", customer_id) if customer_id else None
    merchant = get_context("merchant", merchant_id)

    cust_name = customer.get("identity", {}).get("name", "there") if customer else "there"
    merchant_name = merchant.get("identity", {}).get("name", "") if merchant else ""
    cust_lang = customer.get("identity", {}).get("language_pref", "en") if customer else "en"
    lang_note = "Use Hinglish" if cust_lang == "hi" else "Use clear English"

    prompt = f"""You are Vera composing a reply ON BEHALF of merchant '{merchant_name}' TO customer '{cust_name}'.

Customer just said: "{message}"

Recent conversation:
{json.dumps(conversation[-4:], ensure_ascii=False)}

Rules:
1. Reply TO the customer — address them by name '{cust_name}'
2. Address exactly what they said
3. If they confirmed a slot — confirm it with specific details
4. If they asked a question — answer specifically
5. {lang_note}
6. 2-3 lines max
7. ONE clear CTA at end
8. send_as = merchant_on_behalf

Return ONLY valid JSON:
{{
  "action": "send",
  "body": "reply to customer",
  "cta": "binary_confirm_cancel" or "open_ended" or "none",
  "rationale": "why this reply"
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw = part
                    break

        result = json.loads(raw.strip())
        add_conversation_turn(conversation_id, "vera", result.get("body", ""))
        return {
            "action": result.get("action", "send"),
            "body": result.get("body", ""),
            "cta": result.get("cta", "none"),
            "rationale": result.get("rationale", "")
        }

    except Exception as e:
        body = f"Thank you {cust_name}! Your booking is confirmed. See you soon! 🙏"
        add_conversation_turn(conversation_id, "vera", body)
        return {
            "action": "send",
            "body": body,
            "cta": "none",
            "rationale": f"Fallback: {str(e)}"
        }


def compose_reply_with_claude(
    conversation_id: str,
    merchant_id: str,
    customer_id: str | None,
    message: str,
    conversation: list
) -> dict:
    merchant = get_context("merchant", merchant_id)
    category_slug = merchant.get("category_slug", "") if merchant else ""
    category = get_context("category", category_slug) if category_slug else {}

    merchant_name = merchant.get("identity", {}).get("name", "Merchant") if merchant else "Merchant"
    languages = merchant.get("identity", {}).get("languages", ["en"]) if merchant else ["en"]
    lang_instruction = "Use Hinglish" if "hi" in languages else "Use clear English"

    history_text = ""
    for turn in conversation[-5:]:
        role = "Vera" if turn["role"] == "vera" else "Merchant"
        history_text += f"{role}: {turn['message']}\n"

    prompt = f"""You are Vera, magicpin's WhatsApp AI for merchants.

MERCHANT: {merchant_name}
CATEGORY: {category_slug}

CONVERSATION:
{history_text}
MERCHANT SAID: "{message}"

Reply naturally and move conversation forward.
Rules:
1. Answer their question specifically
2. ONE CTA at end
3. {lang_instruction}
4. 2-4 lines max
5. No URLs

Return ONLY valid JSON:
{{
  "action": "send",
  "body": "your reply",
  "cta": "open_ended" or "binary_yes_no" or "none",
  "rationale": "why this reply"
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw = part
                    break

        result = json.loads(raw.strip())
        add_conversation_turn(conversation_id, "vera", result.get("body", ""))
        return {
            "action": result.get("action", "send"),
            "body": result.get("body", ""),
            "cta": result.get("cta", "open_ended"),
            "rationale": result.get("rationale", "")
        }

    except Exception as e:
        return {
            "action": "send",
            "body": "Ek second — let me pull that up for you.",
            "cta": "none",
            "rationale": f"Fallback: {str(e)}"
        }