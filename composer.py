import os
import json
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = "models/gemini-2.5-flash"

FEW_SHOT_EXAMPLES = """
EXAMPLE 1 — Dentists / research_digest / merchant-facing (50/50)
Category: dentists | Trigger: research_digest | CTR: 2.1% vs peer 3.0%
Merchant signals: high_risk_adult_cohort (124 patients)
Digest: JIDA Oct 2026, p.14 — 2,100-patient trial, 3-month fluoride recall cuts caries 38% better than 6-month
PERFECT MESSAGE:
"Dr. Meera, JIDA's Oct issue landed. One item relevant to your high-risk adult patients — 2,100-patient trial showed 3-month fluoride recall cuts caries recurrence 38% better than 6-month. Worth a look (2-min abstract). Want me to pull it + draft a patient-ed WhatsApp you can share? — JIDA Oct 2026 p.14"
WHY IT SCORES 50/50: Real numbers (2,100 / 38%), source + page, merchant-specific cohort anchor, reciprocity CTA, clinical tone.

EXAMPLE 2 — Dentists / recall_due / customer-facing (49/50)
send_as: merchant_on_behalf | Customer: Priya, lapsed_soft, hi-en mix, weekday evenings
Active offer: Dental Cleaning @ 299 | Available slots: Wed 5 Nov 6pm, Thu 6 Nov 5pm
PERFECT MESSAGE:
"Hi Priya, Dr. Meera's clinic here. It's been 5 months since your last visit — your 6-month cleaning recall is due. Apke liye 2 slots ready hain: Wed 5 Nov, 6pm ya Thu 6 Nov, 5pm. 299 cleaning + complimentary fluoride. Reply 1 for Wed, 2 for Thu, or tell us a time that works."
WHY IT SCORES 49/50: Name + language mix honored, real slots + price, recall framing, multi-choice booking CTA.

EXAMPLE 3 — Salons / trial_followup / customer-facing (47/50)
send_as: merchant_on_behalf | Customer: Kavya, wedding 2026-11-08, Saturday 4pm preference
Merchant: Studio11 Kapra, owner Lakshmi | Offer: 2499 bridal prep (4 sessions + kit)
PERFECT MESSAGE:
"Hi Kavya, Lakshmi from Studio11 Kapra here. 196 days to your wedding — perfect window to start the 30-day skin-prep program before serious bridal bookings roll in. 2499 covers 4 sessions + a take-home kit. Want me to block your preferred Saturday 4pm slot for the first session next week?"
WHY IT SCORES 47/50: Days-to-wedding count, price + package structure, owner name, preference honored, single commit CTA.

EXAMPLE 4 — Salons / curious_ask_due / merchant-facing (44/50)
Merchant: Studio11, owner Lakshmi, growing strongly
GOOD MESSAGE:
"Hi Lakshmi! Quick check — what service has been most asked-for this week at Studio11? I'll turn the answer into a Google post + a 4-line WhatsApp reply you can use when customers ask about pricing. Takes 5 min."
WHY IT SCORES 44/50: Low-stakes question, reciprocity up-front, effort externalized.

EXAMPLE 5 — Restaurants / ipl_match_today / merchant-facing (50/50)
Merchant: SK Pizza Junction, owner Suresh, BOGO pizza active
Trigger: DC vs MI at Arun Jaitley Stadium, 7:30pm today (Saturday)
PERFECT MESSAGE:
"Quick heads-up Suresh — DC vs MI at Arun Jaitley tonight, 7:30pm. Important: Saturday IPL matches usually shift -12% restaurant covers (people watch at home). Skip the match-night promo today; instead push your BOGO pizza (already active) as a delivery-only Saturday special. Want me to draft the Swiggy banner + an Insta story? Live in 10 min."
WHY IT SCORES 50/50: Counter-intuitive insight (-12%), leverages existing offer, concrete deliverables.

EXAMPLE 6 — Restaurants / active_planning_intent / merchant-facing (49/50)
Merchant: Mylari South Indian Cafe, Indiranagar Bangalore, 18 orders/day lunch thali
PERFECT MESSAGE:
"Suresh, here's a starter version — you can edit: Mylari Corporate Thali for offices in Indiranagar. 10 thalis at 125 each + free delivery. 25 thalis at 115 each + 2 free filter coffees. 50+ at 105 each + 1 free dosa platter. 3 offices in Indiranagar are in your delivery radius. Want me to draft a 3-line WhatsApp to send their facilities managers?"
WHY IT SCORES 49/50: Complete drafted artifact, tiered pricing, locality-specific.

EXAMPLE 7 — Gyms / seasonal_perf_dip / merchant-facing (48/50)
Merchant: PowerHouse Fitness, owner Karthik, 245 members, views -30% w/w
PERFECT MESSAGE:
"Karthik, your views are down 30% this week — but this is the normal April-June acquisition lull (every metro gym sees -25 to -35% in this window). Action: skip ad spend now, save it for Sept-Oct when conversion is 2x. Focus retention on your 245 members. Want me to draft a summer attendance challenge to keep them through the dip?"
WHY IT SCORES 48/50: Anxiety pre-emption, data range, real member count, reframe + action proposal.

EXAMPLE 8 — Gyms / customer_lapsed_hard / customer-facing (50/50)
send_as: merchant_on_behalf | Customer: Rashmi, 57 days lapsed, weight-loss goal
Merchant: PowerHouse, owner Karthik | New class: Tue/Thu HIIT 6:30pm, 45 min
PERFECT MESSAGE:
"Hi Rashmi, Karthik from PowerHouse here. It's been about 8 weeks — happens to most members at some point, no judgment. We've added a Tue/Thu evening HIIT class that fits weight-loss goals well (45 min, 6:30pm). Want me to hold a free trial spot for you next Tue, 30 Apr? Reply YES — no commitment, no auto-charge."
WHY IT SCORES 50/50: No-shame framing, goal match, specific class details, removes 2 barriers in one line.

EXAMPLE 9 — Pharmacies / supply_alert / merchant-facing (50/50)
Merchant: Apollo Health Plus, owner Ramesh, 240 chronic-Rx customers
Trigger: recall on atorvastatin batches AT2024-1102 + AT2024-1108, 22 customers affected
PERFECT MESSAGE:
"Ramesh, urgent: voluntary recall on 2 atorvastatin batches (AT2024-1102, AT2024-1108) — sub-potency, no safety risk, but customers should be informed. Pulled your repeat-Rx list: 22 of your 240 chronic-Rx customers were dispensed these batches in last 90 days. Want me to draft their WhatsApp note + the replacement-pickup workflow?"
WHY IT SCORES 50/50: Batch numbers, bounded risk framing, derived count, complete workflow offer.

EXAMPLE 10 — Pharmacies / chronic_refill_due / customer-facing (49/50)
send_as: merchant_on_behalf | Customer: Mr. Sharma, senior, via son's WhatsApp
Medicines: metformin + atorvastatin + telmisartan, run out 28 April
PERFECT MESSAGE:
"Namaste — Apollo Health Plus Malviya Nagar yahan. Sharma ji ki 3 monthly medicines (metformin, atorvastatin, telmisartan) 28 April ko khatam hongi. Same dose, same brand pack ready hai. Senior discount 15% applied — total 1420 (240 saved). Free home delivery to saved address by 5pm tomorrow. Reply CONFIRM to dispatch, or call 9876543210 if any change in dosage."
WHY IT SCORES 49/50: Namaste salutation, molecule names, exact date + total + savings, two-channel option.

KEY PATTERNS:
1. Always use owner first name
2. Always cite source for research/compliance
3. Always use real numbers from context — never invent
4. ONE CTA at the end only
5. Domain vocabulary used correctly
6. Customer language preference honored
7. Bot adds judgment beyond the trigger
8. Effort externalized
9. No URLs, no taboo words, no generic phrases
10. Rationale must match the message
"""


def build_prompt(category: dict, merchant: dict, trigger: dict, customer: dict | None) -> str:
    trigger_kind = trigger.get("kind", "unknown")
    merchant_name = merchant.get("identity", {}).get("name", "Merchant")
    owner_name = merchant.get("identity", {}).get("owner_first_name", "")
    city = merchant.get("identity", {}).get("city", "")
    locality = merchant.get("identity", {}).get("locality", "")
    languages = merchant.get("identity", {}).get("languages", ["en"])
    category_slug = merchant.get("category_slug", "")

    perf = merchant.get("performance", {})
    views = perf.get("views", 0)
    calls = perf.get("calls", 0)
    ctr = perf.get("ctr", 0)
    delta_7d = perf.get("delta_7d", {})

    peer_stats = category.get("peer_stats", {})
    peer_ctr = peer_stats.get("avg_ctr", 0)
    peer_avg_views = peer_stats.get("avg_views_30d", 0)
    peer_retention = peer_stats.get("retention_6mo_pct", 0)

    offers = merchant.get("offers", [])
    active_offers = [o for o in offers if o.get("status") == "active"]
    expired_offers = [o for o in offers if o.get("status") == "expired"]
    active_offer_titles = [o.get("title", "") for o in active_offers]

    signals = merchant.get("signals", [])
    voice = category.get("voice", {})
    tone = voice.get("tone", "professional")
    taboos = voice.get("vocab_taboo", [])
    vocab_allowed = voice.get("vocab_allowed", [])
    salutation_examples = voice.get("salutation_examples", [])

    digest = category.get("digest", [])
    digest_text = json.dumps(digest[:3], ensure_ascii=False) if digest else "none"
    seasonal_beats = category.get("seasonal_beats", [])
    trend_signals = category.get("trend_signals", [])

    conv_history = merchant.get("conversation_history", [])
    last_messages = conv_history[-3:] if conv_history else []

    customer_agg = merchant.get("customer_aggregate", {})
    lapsed = customer_agg.get("lapsed_180d_plus", 0)
    retention = customer_agg.get("retention_6mo_pct", 0)
    total_customers = customer_agg.get("total_unique_ytd", 0)
    high_risk = customer_agg.get("high_risk_adult_count", 0)

    review_themes = merchant.get("review_themes", [])
    trigger_payload = trigger.get("payload", {})
    trigger_urgency = trigger.get("urgency", 2)
    suppression_key = trigger.get("suppression_key", "")

    lang_instruction = (
        "Use natural Hindi-English code-mix (Hinglish)."
        if "hi" in languages
        else "Use clear, conversational English."
    )

    send_as = "vera"
    customer_section = ""
    if customer:
        send_as = "merchant_on_behalf"
        cust_name = customer.get("identity", {}).get("name", "Customer")
        cust_lang = customer.get("identity", {}).get("language_pref", "en")
        cust_state = customer.get("state", "active")
        relationship = customer.get("relationship", {})
        last_visit = relationship.get("last_visit", "")
        visits_total = relationship.get("visits_total", 0)
        services = relationship.get("services_received", [])
        preferred_slots = customer.get("preferences", {}).get("preferred_slots", "")
        available_slots = trigger_payload.get("available_slots", [])
        consent_scope = customer.get("consent", {}).get("scope", [])

        customer_section = f"""
CUSTOMER CONTEXT
Send ON BEHALF of merchant TO customer. send_as = merchant_on_behalf

Customer name: {cust_name}
Language preference: {cust_lang}
State: {cust_state}
Last visit: {last_visit}
Total visits: {visits_total}
Services received: {', '.join(services)}
Preferred slots: {preferred_slots}
Available slots: {json.dumps(available_slots, ensure_ascii=False)}
Consent scope: {', '.join(consent_scope)}
"""

    trigger_instructions = get_trigger_instructions(
        trigger_kind, trigger_payload, category, merchant, customer
    )

    return f"""You are Vera, magicpin's AI assistant for Indian merchant growth.
Compose ONE highly specific WhatsApp message that scores 50/50 on the judge rubric.

{FEW_SHOT_EXAMPLES}

Now compose for this context:

MERCHANT
Name: {merchant_name}
Owner: {owner_name if owner_name else 'not provided'}
Category: {category_slug}
Location: {locality}, {city}
Languages: {', '.join(languages)}
Plan: {merchant.get('subscription', {}).get('plan', 'unknown')}, {merchant.get('subscription', {}).get('days_remaining', 0)} days left

Performance (30d):
  Views: {views} (peer avg: {peer_avg_views})
  Calls: {calls}
  CTR: {ctr:.3f} (peer: {peer_ctr:.3f}) {'below peer' if ctr < peer_ctr else 'above peer'}
  7d delta: views {delta_7d.get('views_pct', 0):.0%}, calls {delta_7d.get('calls_pct', 0):.0%}

Active offers: {', '.join(active_offer_titles) if active_offer_titles else 'NONE'}
Expired offers: {', '.join([o.get('title','') for o in expired_offers]) if expired_offers else 'none'}

Customers: {total_customers} total, {lapsed} lapsed 180d+, {retention:.0%} retention (peer: {peer_retention:.0%}), {high_risk if high_risk else 'N/A'} high-risk
Signals: {', '.join(signals) if signals else 'none'}
Reviews: {json.dumps(review_themes, ensure_ascii=False) if review_themes else 'none'}
Recent conversation: {json.dumps(last_messages, ensure_ascii=False) if last_messages else 'none'}

CATEGORY VOICE
Tone: {tone}
Allowed vocab: {', '.join(vocab_allowed[:8]) if vocab_allowed else 'standard'}
Never use: {', '.join(taboos)}
Salutation: {', '.join(salutation_examples) if salutation_examples else 'Hi [name]'}
Seasonal: {json.dumps(seasonal_beats[:2], ensure_ascii=False)}
Trends: {json.dumps(trend_signals[:2], ensure_ascii=False)}
Digest: {digest_text}

TRIGGER
Kind: {trigger_kind}
Urgency: {trigger_urgency}/5
Suppression key: {suppression_key}
Payload: {json.dumps(trigger_payload, ensure_ascii=False)}
{customer_section}

INSTRUCTIONS FOR THIS TRIGGER TYPE
{trigger_instructions}

RULES
1. Use REAL numbers from context — never invent
2. Use owner first name: "{owner_name}"
3. ONE CTA at the very end
4. Never use: {', '.join(taboos)}
5. No URLs
6. No "Hope you're doing well" openers
7. 3-5 lines max
8. {lang_instruction}
9. Cite sources for research/compliance
10. send_as = "{send_as}"

IMPORTANT: You MUST respond with ONLY a valid JSON object. Do NOT write plain text. Do NOT include any explanation before or after the JSON.
Start your response with {{ and end with }}.

JSON OUTPUT (fill in the values):
{{
  "body": "the complete WhatsApp message here",
  "cta": "open_ended",
  "send_as": "{send_as}",
  "suppression_key": "{suppression_key}",
  "rationale": "1-2 sentences: what signal prompted this, what it achieves"
}}"""


def get_trigger_instructions(kind, payload, category, merchant, customer):
    digest = category.get("digest", [])
    peer_stats = category.get("peer_stats", {})
    perf = merchant.get("performance", {})
    active_offers = [o for o in merchant.get("offers", []) if o.get("status") == "active"]

    instructions = {
        "research_digest": f"""Lead with SPECIFIC finding (trial size, %, source+page).
Connect to THIS merchant's patient/customer cohort.
Offer to do useful work (draft post, share abstract).
Digest: {json.dumps(digest[:2], ensure_ascii=False)}
CTA: open_ended""",

        "recall_due": f"""Send AS merchant TO customer (merchant_on_behalf).
State exactly how long since last visit.
Offer 2 specific slots from trigger payload.
Include real price: {[o.get('title') for o in active_offers]}
CTA: Reply 1 for slot A, 2 for slot B""",

        "perf_spike": f"""Name exact spike number + percentage.
Views: {perf.get('views',0)}, delta: {perf.get('delta_7d',{}).get('views_pct',0):.0%}
Frame as: capitalize RIGHT NOW while traffic is high.
CTA: binary YES/NO""",

        "perf_dip": f"""Name exact dip with peer comparison.
CTR: {perf.get('ctr',0):.3f} vs peer {peer_stats.get('avg_ctr',0):.3f}
Frame as loss aversion. Suggest ONE concrete fix.
CTA: binary YES/NO""",

        "seasonal_perf_dip": """Acknowledge dip number, immediately reframe as normal seasonal pattern.
Give peer range for this season.
Suggest: save ad spend, focus on retaining existing customers.
CTA: open_ended""",

        "festival_upcoming": """Name festival + exact days remaining.
Suggest festival-specific campaign using active offers.
Frame urgency: last X days to set this up.
CTA: binary YES/NO""",

        "ipl_match_today": f"""Name teams + venue + time.
ADD JUDGMENT: Saturday = delivery opportunity, weeknight = dine-in spike.
Use active offers: {[o.get('title') for o in active_offers]}
Offer concrete deliverable (banner + story, live in 10 min).
CTA: binary YES/NO""",

        "competitor_opened": """Do not alarm. Frame as: strengthen your position now.
Suggest ONE defensive action.
Use social proof.
CTA: binary YES/NO""",

        "review_theme_emerged": """Name SPECIFIC theme + number of mentions.
Positive: suggest amplifying. Negative: suggest ONE fix.
CTA: open_ended""",

        "milestone_reached": """Celebrate briefly, immediately pivot to next move.
Use peer comparison.
CTA: open_ended or binary""",

        "dormant_with_vera": """Lead with ONE interesting insight they would not know without Vera.
Zero guilt. Zero commitment.
CTA: curiosity question""",

        "curious_ask_due": """Ask ONE specific question. Make a SPECIFIC GUESS to make it easy.
Offer to turn answer into something useful immediately.
Under 3 lines.
CTA: open_ended""",

        "renewal_due": f"""State exact days remaining.
Frame value in SPECIFIC terms: {perf.get('views',0)} views, {perf.get('calls',0)} calls last 30 days.
CTA: binary YES/NO""",

        "winback_eligible": """Reference specific lapse duration.
Suggest targeted win-back offer.
Frame as easy: I can draft it now.
CTA: binary YES/NO""",

        "customer_lapsed_hard": """Warm, NO shame, NO guilt.
Reference their specific goal or service history.
Introduce something NEW that matches their goal.
Remove barriers explicitly.
CTA: single binary YES with specific date""",

        "supply_alert": """State issue with SPECIFIC identifiers (batch numbers, circular).
Bound the risk clearly.
Derive count of affected customers from merchant data.
Offer complete workflow.
CTA: open_ended""",

        "chronic_refill_due": """Name SPECIFIC medicines (molecule names).
State exact run-out date. Show total + savings.
Offer delivery with time window.
Two-channel option for seniors. Namaste for senior customers.
CTA: binary CONFIRM""",

        "gbp_unverified": """State what is at stake (missed searches, lower ranking).
Make it specific to their locality.
Offer to walk through verification (5-10 min).
CTA: binary YES/NO""",

        "cde_opportunity": """Name specific event, date, and relevance to their practice.
Collegial peer-to-peer tone.
CTA: open_ended""",

        "regulation_change": f"""REGULATION CHANGE — New compliance requirement just announced.
Name the specific regulation, authority, and deadline.
Derive impact on THIS merchant's practice/setup.
Offer to help with compliance checklist or audit.
Digest: {json.dumps(digest[:2], ensure_ascii=False)}
CTA: open_ended""",

        "appointment_tomorrow": """APPOINTMENT REMINDER — Customer has appointment tomorrow.
Send AS merchant TO customer (merchant_on_behalf).
Confirm the appointment time and location clearly.
Add one helpful preparation tip.
CTA: binary CONFIRM or ask to reschedule""",

        "customer_lapsed_soft": """SOFT LAPSE — Customer has not visited in a while but not gone long.
Warm re-engagement, no pressure.
Mention something new or relevant since their last visit.
CTA: binary YES to book""",

        "trial_followup": """TRIAL FOLLOWUP — Customer completed a trial session.
Reference what they tried specifically.
Share one result or benefit they experienced.
Offer to continue with a specific next step.
CTA: binary YES/NO""",
    }

    return instructions.get(kind, f"""{kind.upper()} TRIGGER
Lead with the specific event or signal that prompted this.
Connect to ONE actionable thing for this merchant.
Use real numbers and active offers.
Add judgment — interpret what this means for them.
ONE clear CTA at the end.""")


def _call_gemini(prompt: str, max_tokens: int = 1000, retries: int = 3) -> str:
    """Call Gemini with retry on 429 rate-limit errors."""
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=8192,
                )
            )
            return response.text.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                wait = (attempt + 1) * 20
                print(f"[GEMINI] 429 rate-limit, waiting {wait}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Gemini still rate-limited after {retries} retries")


def _parse_json_response(raw: str) -> dict:
    """Strip markdown fences and parse JSON from Gemini response."""
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break
    return json.loads(raw.strip())


def compose(category, merchant, trigger, customer=None):
    prompt = build_prompt(category, merchant, trigger, customer)
    raw = ""

    try:
        print(f"[COMPOSE] calling Gemini API for trigger kind: {trigger.get('kind')}")
        raw = _call_gemini(prompt, max_tokens=1000)
        print(f"[COMPOSE] got response length: {len(raw)}")
        print(f"[COMPOSE] first 300 chars: {raw[:300]}")

        result = _parse_json_response(raw)
        body = result.get("body", "")
        print(f"[COMPOSE] parsed body length: {len(body)}")

        return {
            "body": body,
            "cta": result.get("cta", "open_ended"),
            "send_as": result.get("send_as", "vera"),
            "suppression_key": result.get("suppression_key", trigger.get("suppression_key", "")),
            "rationale": result.get("rationale", "")
        }

    except json.JSONDecodeError as e:
        print(f"[COMPOSE JSON ERROR] {str(e)}")
        print(f"[COMPOSE JSON ERROR] raw was: {raw[:300]}")
        return {
            "body": "",
            "cta": "none",
            "send_as": "vera",
            "suppression_key": trigger.get("suppression_key", ""),
            "rationale": f"JSON parse error: {str(e)}"
        }

    except Exception as e:
        print(f"[COMPOSE ERROR] {type(e).__name__}: {str(e)}")
        return {
            "body": "",
            "cta": "none",
            "send_as": "vera",
            "suppression_key": trigger.get("suppression_key", ""),
            "rationale": f"Error: {str(e)}"
        }