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
    "aapki jaankari ke liye bahut-bahut shukriya",
    "main aapki yeh sabhi baatein",
    "hamari team tak pahuncha",
]

INTENT_PHRASES = [
    "let's do it",
    "lets do it",
    "ok do it",
    "yes do it",
    "go ahead",
    "please go ahead",
    "haan karo",
    "kar do",
    "chaliye",
    "chalo karte hain",
    "yes please",
    "yes, please",
    "sounds good",
    "ok proceed",
    "proceed",
    "confirm",
    "i want to join",
    "mujhe join karna hai",
    "sign me up",
]


STOP_PHRASES = [
    "stop",
    "not interested",
    "no thanks",
    "no thank you",
    "leave me alone",
    "don't message",
    "dont message",
    "unsubscribe",
    "band karo",
    "mat bhejo",
    "nahi chahiye",
    "boring",
    "useless",
    "waste of time",
    "stop messaging",
    "stop sending",
]
OFF_TOPIC_PHRASES = [
    "gst",
    "income tax",
    "filing",
    "loan",
    "insurance",
    "legal",
    "court",
    "police",
    "help me with",
    "can you also",
]

HOSTILE_PHRASES = [
    "idiot",
    "stupid",
    "useless bot",
    "worst",
    "bakwas",
    "bekar",
    "chutiya",
    "bc",
    "mc",
]

def is_auto_reply(message: str) -> bool:
    """
    Detect if the message is a WhatsApp Business auto-reply.
    """
    message_lower = message.lower().strip()
    for pattern in AUTO_REPLY_PATTERNS:
        if pattern in message_lower:
            return True
    return False


def is_intent_transition(message: str) -> bool:
    """
    Detect if merchant is signalling they want to take action.
    """
    message_lower = message.lower().strip()
    for phrase in INTENT_PHRASES:
        if phrase in message_lower:
            return True
    return False


def is_hard_stop(message: str) -> bool:
    """
    Detect if merchant explicitly wants to stop.
    """
    message_lower = message.lower().strip()
    for phrase in STOP_PHRASES:
        if phrase in message_lower:
            return True
    return False


def count_auto_replies(conversation: list) -> int:
    """
    Count how many consecutive auto-replies have been received.
    """
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
    turn_number: int
) -> dict:
    """
    Main reply handler.
    Decides what action to take based on the merchant's message.
    Returns: {action, body?, cta?, rationale, wait_seconds?}
    """

    add_conversation_turn(conversation_id, "merchant", message)

    conversation = get_conversation(conversation_id)

    if is_hard_stop(message):
        return {
            "action": "end",
            "rationale": "Merchant explicitly opted out or expressed disinterest. Closing conversation and suppressing future messages."
        }

    if any(phrase in message.lower() for phrase in HOSTILE_PHRASES):
        return {
            "action": "send",
            "body": "Samajh sakta hoon — agar kabhi listing ya campaigns pe kaam karna ho toh batayein. 🙏",
            "cta": "none",
            "rationale": "Hostile message detected. Responded politely and left door open."
    }


    if any(phrase in message.lower() for phrase in OFF_TOPIC_PHRASES):
        return {
            "action": "send",
            "body": "GST/legal matters meri expertise nahi hai — uske liye CA se baat karein. Main aapki magicpin listing aur customers ke liye yahan hoon. Kuch aur help karoon?",
            "cta": "open_ended",
            "rationale": "Off-topic request detected. Politely declined and redirected."
    }

    if is_auto_reply(message):
        auto_reply_count = count_auto_replies(conversation)

        if auto_reply_count == 1:

            return {
                "action": "send",
                "body": "Looks like an automated reply 😊 When you get a chance, just reply YES to continue.",
                "cta": "binary_yes_no",
                "rationale": "Detected first auto-reply. Sending one gentle nudge for the owner to see."
            }
        elif auto_reply_count == 2:

            return {
                "action": "wait",
                "wait_seconds": 14400, 
                "rationale": "Second consecutive auto-reply detected. Backing off 4 hours to wait for owner."
            }
        else:

            return {
                "action": "end",
                "rationale": "Auto-reply detected 3+ times. Owner not available. Closing conversation."
            }

    if is_intent_transition(message):
        
        merchant = get_context("merchant", merchant_id)
        if merchant:
            offers = merchant.get("offers", [])
            active_offers = [o for o in offers if o.get("status") == "active"]
            offer_title = active_offers[0].get("title", "") if active_offers else ""
            owner_name = merchant.get("identity", {}).get("owner_first_name", "")
            customer_agg = merchant.get("customer_aggregate", {})
            total_customers = customer_agg.get("total_unique_ytd", 0)

            action_body = f"Perfect{', ' + owner_name if owner_name else ''}! Setting it up now."
            if offer_title and total_customers:
                action_body += f" I'll draft the campaign with your '{offer_title}' offer for your {total_customers} customers. Reply CONFIRM to send."
            else:
                action_body += " What's the first thing you'd like to tackle — profile update, campaign, or customer outreach? Reply with your choice."

            add_conversation_turn(conversation_id, "vera", action_body)
            return {
                "action": "send",
                "body": action_body,
                "cta": "binary_confirm_cancel",
                "rationale": "Merchant signalled intent to act. Switching from qualifying to action mode immediately."
            }


    return compose_reply_with_claude(
        conversation_id,
        merchant_id,
        customer_id,
        message,
        conversation
    )


def compose_reply_with_claude(
    conversation_id: str,
    merchant_id: str,
    customer_id: str | None,
    message: str,
    conversation: list
) -> dict:
    """
    Use Claude to compose a contextual reply for normal messages.
    """


    merchant = get_context("merchant", merchant_id)
    category_slug = merchant.get("category_slug", "") if merchant else ""
    category = get_context("category", category_slug) if category_slug else {}

    merchant_name = merchant.get("identity", {}).get("name", "Merchant") if merchant else "Merchant"
    languages = merchant.get("identity", {}).get("languages", ["en"]) if merchant else ["en"]

    lang_instruction = "Use Hindi-English mix (Hinglish)" if "hi" in languages else "Use clear English"

  
    history_text = ""
    for turn in conversation[-5:]: 
        role = "Vera" if turn["role"] == "vera" else "Merchant"
        history_text += f"{role}: {turn['message']}\n"

    prompt = f"""You are Vera, magicpin's WhatsApp AI assistant for merchants.

MERCHANT: {merchant_name}
CATEGORY: {category_slug}

CONVERSATION SO FAR:
{history_text}
MERCHANT JUST SAID: "{message}"

Your job: Reply to the merchant's message naturally and move the conversation forward.

RULES:
1. Stay on topic — if merchant asks something off-topic (GST, unrelated queries), politely decline and redirect
2. If merchant asked a question, answer it specifically
3. If merchant gave information, use it to take the next step
4. ONE clear CTA at the end
5. {lang_instruction}
6. Keep it SHORT — 2-4 lines max
7. NO URLs
8. NO generic phrases

Return ONLY valid JSON:
{{
  "action": "send",
  "body": "your reply here",
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

      
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)

     
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
            "body": "Ek second — let me check that for you.",
            "cta": "none",
            "rationale": f"Fallback reply due to error: {str(e)}"
        }