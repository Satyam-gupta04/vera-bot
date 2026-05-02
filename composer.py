
import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

FEW_SHOT_EXAMPLES = """

EXAMPLE 1 — Dentists / research_digest / merchant-facing (50/50)
Category: dentists | Trigger: research_digest | CTR: 2.1% vs peer 3.0%
Merchant signals: high_risk_adult_cohort (124 patients)
Digest: JIDA Oct 2026, p.14 — 2,100-patient trial, 3-month fluoride recall cuts caries 38% better than 6-month
→ PERFECT MESSAGE:
"Dr. Meera, JIDA's Oct issue landed. One item relevant to your high-risk adult patients — 2,100-patient trial showed 3-month fluoride recall cuts caries recurrence 38% better than 6-month. Worth a look (2-min abstract). Want me to pull it + draft a patient-ed WhatsApp you can share? — JIDA Oct 2026 p.14"
WHY IT SCORES 50/50: Real numbers (2,100 / 38%), source + page, merchant-specific cohort anchor, reciprocity CTA, clinical tone, no taboo words.

---

EXAMPLE 2 — Dentists / recall_due / customer-facing (49/50)
send_as: merchant_on_behalf | Customer: Priya, lapsed_soft, hi-en mix, weekday evenings
Active offer: Dental Cleaning @ ₹299 | Available slots: Wed 5 Nov 6pm, Thu 6 Nov 5pm
→ PERFECT MESSAGE:
"Hi Priya, Dr. Meera's clinic here  It's been 5 months since your last visit — your 6-month cleaning recall is due. Apke liye 2 slots ready hain: Wed 5 Nov, 6pm ya Thu 6 Nov, 5pm. ₹299 cleaning + complimentary fluoride. Reply 1 for Wed, 2 for Thu, or tell us a time that works."
WHY IT SCORES 49/50: Name + language mix honored, real slots + price, recall framing, emoji warmth, multi-choice booking CTA.

---

EXAMPLE 3 — Salons / trial_followup / customer-facing (47/50)
send_as: merchant_on_behalf | Customer: Kavya, wedding 2026-11-08, Saturday 4pm preference
Merchant: Studio11 Kapra, owner Lakshmi | Offer: ₹2,499 bridal prep (4 sessions + kit)
→ PERFECT MESSAGE:
"Hi Kavya  Lakshmi from Studio11 Kapra here. 196 days to your wedding — perfect window to start the 30-day skin-prep program before serious bridal bookings roll in. ₹2,499 covers 4 sessions + a take-home kit. Want me to block your preferred Saturday 4pm slot for the first session next week?"
WHY IT SCORES 47/50: Days-to-wedding count, price + package structure, owner name, preference honored, single commit CTA.

---

EXAMPLE 4 — Salons / curious_ask_due / merchant-facing (44/50)
Merchant: Studio11, owner Lakshmi, growing strongly
→ GOOD MESSAGE:
"Hi Lakshmi! Quick check — what service has been most asked-for this week at Studio11? I'll turn the answer into a Google post + a 4-line WhatsApp reply you can use when customers ask about pricing. Takes 5 min."
WHY IT SCORES 44/50: Low-stakes question, reciprocity up-front (Google post + reply), effort externalized (5 min). Could be sharper with a service guess.

---

EXAMPLE 5 — Restaurants / ipl_match_today / merchant-facing (50/50)
Merchant: SK Pizza Junction, owner Suresh, BOGO pizza active (Tue-Thu)
Trigger: DC vs MI at Arun Jaitley Stadium, 7:30pm today (Saturday)
→ PERFECT MESSAGE:
"Quick heads-up Suresh — DC vs MI at Arun Jaitley tonight, 7:30pm. Important: Saturday IPL matches usually shift -12% restaurant covers (people watch at home). Skip the match-night promo today; instead push your BOGO pizza (already active) as a delivery-only Saturday special. Want me to draft the Swiggy banner + an Insta story? Live in 10 min."
WHY IT SCORES 50/50: Counter-intuitive insight (-12%), leverages existing offer, concrete deliverables, 10-min effort cap. Bot added judgment beyond the trigger.

---

EXAMPLE 6 — Restaurants / active_planning_intent / merchant-facing (49/50)
Merchant: Mylari South Indian Cafe, Indiranagar Bangalore, 18 orders/day lunch thali
Merchant asked about corporate bulk thali — said "yes good idea, what would it look like"
→ PERFECT MESSAGE:
"Suresh, here's a starter version — you can edit:

Mylari Corporate Thali — for offices in Indiranagar
- 10 thalis @ ₹125 each (₹25 off retail) + free delivery
- 25 thalis @ ₹115 each + 2 free filter coffees
- 50+: ₹105 each + 1 free dosa platter
- WhatsApp the day-before by 5pm; we deliver between 12:30-1pm

3 offices in Indiranagar are in your delivery radius (Embassy Tech, RMZ Eco, Sigma Soft). Want me to draft a 3-line WhatsApp to send their facilities managers?"
WHY IT SCORES 49/50: Complete drafted artifact, tiered pricing, named buildings, follow-on offer for outreach.

---

EXAMPLE 7 — Gyms / seasonal_perf_dip / merchant-facing (48/50)
Merchant: PowerHouse Fitness, HSR Layout, owner Karthik, 245 members, views -30% w/w
Trigger: April-June seasonal dip (expected, not alarming)
→ PERFECT MESSAGE:
"Karthik, your views are down 30% this week — but I want to flag this is the normal April-June acquisition lull (every metro gym sees -25 to -35% in this window). Action: skip ad spend now, save it for Sept-Oct when conversion is 2x. For now, focus retention on your 245 members. Want me to draft a 'summer attendance challenge' to keep them through the dip?"
WHY IT SCORES 48/50: Anxiety pre-emption, data range (-25 to -35%), real member count, reframe + action proposal.

---

EXAMPLE 8 — Gyms / customer_lapsed_hard / customer-facing (50/50)
send_as: merchant_on_behalf | Customer: Rashmi, 57 days lapsed, weight-loss goal, 5-month member
Merchant: PowerHouse, owner Karthik | Offer: first month @ ₹499
New class: Tue/Thu evening HIIT, 6:30pm, 45 min
→ PERFECT MESSAGE:
"Hi Rashmi  Karthik from PowerHouse here. It's been about 8 weeks — happens to most members at some point, no judgment. We've added a Tue/Thu evening HIIT class that fits weight-loss goals well (45 min, 6:30pm). Want me to hold a free trial spot for you next Tue, 30 Apr? Reply YES — no commitment, no auto-charge."
WHY IT SCORES 50/50: No-shame framing, goal match, specific class details, date, removes 2 barriers ("no judgment" + "no commitment") in one line.

---

EXAMPLE 9 — Pharmacies / supply_alert / merchant-facing (50/50)
Merchant: Apollo Health Plus, Malviya Nagar Jaipur, owner Ramesh, 240 chronic-Rx customers
Trigger: voluntary recall on atorvastatin batches AT2024-1102 + AT2024-1108
22 of 240 customers dispensed these batches in last 90 days
→ PERFECT MESSAGE:
"Ramesh, urgent: voluntary recall on 2 atorvastatin batches (AT2024-1102, AT2024-1108) by Mfr Z — sub-potency, no safety risk, but customers should be informed for replacement. Pulled your repeat-Rx list: 22 of your chronic-Rx customers were dispensed these batches in last 90 days. Want me to draft their WhatsApp note + the replacement-pickup workflow?"
WHY IT SCORES 50/50: Batch numbers, bounded risk framing ("no safety risk"), derived count (22/240), complete workflow offer.

---

EXAMPLE 10 — Pharmacies / chronic_refill_due / customer-facing (49/50)
send_as: merchant_on_behalf | Customer: Mr. Sharma (senior, 65-75), via son's WhatsApp
Medicines: metformin + atorvastatin + telmisartan, run out 28 April
Active offers: senior 15% off, free home delivery >₹499
→ PERFECT MESSAGE:
"Namaste — Apollo Health Plus Malviya Nagar yahan. Sharma ji ki 3 monthly medicines (metformin, atorvastatin, telmisartan) 28 April ko khatam hongi. Same dose, same brand pack ready hai. Senior discount 15% applied — total ₹1,420 (₹240 saved). Free home delivery to saved address by 5pm tomorrow. Reply CONFIRM to dispatch, or call 9876543210 if any change in dosage."
WHY IT SCORES 49/50: Namaste salutation, molecule names, exact date + total + savings, two-channel option (reply OR call), senior norms honored.

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


    if "hi" in languages:
        lang_instruction = "Use natural Hindi-English code-mix (Hinglish). Mix both languages the way Indian merchants actually speak — not forced, not 100% Hindi."
    else:
        lang_instruction = "Use clear, conversational English."


    customer_section = ""
    send_as = "vera"
    if customer:
        send_as = "merchant_on_behalf"
        cust_name = customer.get("identity", {}).get("name", "Customer")
        cust_lang = customer.get("identity", {}).get("language_pref", "en")
        cust_state = customer.get("state", "active")
        relationship = customer.get("relationship", {})
        last_visit = relationship.get("last_visit", "")
        visits_total = relationship.get("visits_total", 0)
        services = relationship.get("services_received", [])
        preferences = customer.get("preferences", {})
        preferred_slots = preferences.get("preferred_slots", "")
        available_slots = trigger_payload.get("available_slots", [])
        consent_scope = customer.get("consent", {}).get("scope", [])

        customer_section = f"""

This message is sent ON BEHALF of the merchant TO their customer
send_as = merchant_on_behalf

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

    prompt = f"""You are Vera, magicpin's AI assistant for Indian merchant growth.
Your job: Compose ONE highly specific WhatsApp message that would score 50/50 on the judge rubric.

{FEW_SHOT_EXAMPLES}

Now compose a message for this specific context:


Business name: {merchant_name}
Owner first name: {owner_name if owner_name else 'not provided'}
Category: {category_slug}
Location: {locality}, {city}
Languages: {', '.join(languages)}
Subscription: {merchant.get('subscription', {}).get('plan', 'unknown')} plan, {merchant.get('subscription', {}).get('days_remaining', 0)} days remaining

Performance (last 30 days):
  Views: {views} (peer avg: {peer_avg_views})
  Calls: {calls}
  CTR: {ctr:.3f} (peer median: {peer_ctr:.3f}) {'⬇ BELOW PEER' if ctr < peer_ctr else '⬆ ABOVE PEER'}
  7-day delta: views {delta_7d.get('views_pct', 0):.0%}, calls {delta_7d.get('calls_pct', 0):.0%}

Active offers: {', '.join(active_offer_titles) if active_offer_titles else 'NONE'}
Expired offers: {', '.join([o.get('title','') for o in expired_offers]) if expired_offers else 'none'}

Customer data:
  Total customers YTD: {total_customers}
  Lapsed (180d+): {lapsed}
  Retention 6mo: {retention:.0%} (peer: {peer_retention:.0%})
  High risk adults: {high_risk if high_risk else 'N/A'}

Signals: {', '.join(signals) if signals else 'none'}
Review themes: {json.dumps(review_themes, ensure_ascii=False) if review_themes else 'none'}
Recent conversation: {json.dumps(last_messages, ensure_ascii=False) if last_messages else 'none'}


Tone: {tone}
Allowed vocabulary: {', '.join(vocab_allowed[:8]) if vocab_allowed else 'standard'}
NEVER use: {', '.join(taboos)}
Salutation style: {', '.join(salutation_examples) if salutation_examples else 'Hi [name]'}
Seasonal context: {json.dumps(seasonal_beats[:2], ensure_ascii=False)}
Trend signals: {json.dumps(trend_signals[:2], ensure_ascii=False)}
Latest digest: {digest_text}


Kind: {trigger_kind}
Urgency: {trigger_urgency}/5
Suppression key: {suppression_key}
Full payload: {json.dumps(trigger_payload, ensure_ascii=False)}

{customer_section}


{trigger_instructions}


1. Use REAL numbers from context — NEVER invent data
2. Use owner first name if available: "{owner_name}"
3. ONE CTA at the very end — never in the middle
4. NEVER use: {', '.join(taboos)}
5. NEVER add URLs
6. NEVER start with "Hope you're doing well" or similar
7. Keep it 3-5 lines max
8. {lang_instruction}
9. Use domain vocabulary correctly: {', '.join(vocab_allowed[:5]) if vocab_allowed else 'appropriate terms'}
10. Add judgment — don't just template the trigger, interpret it
11. send_as = "{send_as}"
12. Cite sources for research/compliance items (journal, page, circular number)


{{
  "body": "the complete WhatsApp message",
  "cta": "open_ended" or "binary_yes_no" or "binary_confirm_cancel" or "none",
  "send_as": "{send_as}",
  "suppression_key": "{suppression_key}",
  "rationale": "1-2 sentences: what signal prompted this, what it should achieve"
}}"""

    return prompt


def get_trigger_instructions(
    kind: str,
    payload: dict,
    category: dict,
    merchant: dict,
    customer: dict | None
) -> str:
    """
    Trigger-specific composition instructions.
    Each kind has a different message shape, urgency, and CTA pattern.
    """

    digest = category.get("digest", [])
    peer_stats = category.get("peer_stats", {})
    perf = merchant.get("performance", {})
    offers = merchant.get("offers", [])
    active_offers = [o for o in offers if o.get("status") == "active"]

    instructions = {

        "research_digest": f"""
RESEARCH DIGEST — New research/compliance item dropped.
Shape: Lead with the SPECIFIC finding (trial size, %, source+page).
Then connect to THIS merchant's patient/customer cohort.
Then offer to do useful work (draft post, share abstract, prepare patient message).
Digest items to use: {json.dumps(digest[:2], ensure_ascii=False)}
CTA: open_ended ("Want me to pull it + draft X?")
""",

        "recall_due": f"""
RECALL REMINDER — Customer's service recall window is due.
Shape: Send AS merchant TO customer (merchant_on_behalf).
Open with merchant name + warm greeting.
State exactly how long since last visit.
Offer 2 specific time slots from trigger payload.
Include real price from active offers: {[o.get('title') for o in active_offers]}
CTA: multi-choice slot (Reply 1 for X, 2 for Y)
Language: honor customer's language preference exactly.
""",

        "perf_spike": f"""
PERFORMANCE SPIKE — Merchant's numbers went up.
Shape: Name the exact spike number + percentage.
Views: {perf.get('views', 0)}, delta: {perf.get('delta_7d', {}).get('views_pct', 0):.0%}
Frame as: "right now is the moment to capitalize".
Suggest ONE action — activating an offer, posting content, running a campaign.
CTA: binary YES/NO.
""",

        "perf_dip": f"""
PERFORMANCE DIP — Numbers dropped.
Shape: Name the exact dip with peer comparison.
CTR: {perf.get('ctr', 0):.3f} vs peer {peer_stats.get('avg_ctr', 0):.3f}
Frame as loss aversion — "X searches are finding competitors instead".
Suggest ONE concrete fix.
Do NOT be alarming — be constructive and solution-first.
CTA: binary YES/NO to fix it.
""",

        "seasonal_perf_dip": f"""
SEASONAL DIP — Expected seasonal drop, not a real problem.
Shape: Acknowledge the dip NUMBER first, then immediately reframe as normal.
Give the peer range for this season (e.g., "every gym sees -25 to -35% in April-June").
Suggest: save ad spend now, focus on retention of existing customers.
Propose one retention action (challenge, event, special offer for members).
CTA: open_ended.
""",

        "festival_upcoming": f"""
FESTIVAL TRIGGER — Festival approaching.
Shape: Name the festival + exact days remaining.
Suggest a festival-specific offer or campaign using their ACTIVE offers.
Frame urgency: "last X days to set this up before the window closes".
Offer to draft the campaign material.
CTA: binary YES/NO.
""",

        "ipl_match_today": f"""
IPL MATCH — Cricket match happening today.
Shape: Name teams + venue + time.
ADD JUDGMENT: Saturday/Sunday matches = people watch at home = delivery opportunity.
Weeknight matches = dine-in spike.
Leverage their existing active offers: {[o.get('title') for o in active_offers]}
Suggest the RIGHT action based on match timing — be contrarian if needed.
CTA: binary YES/NO with concrete deliverable ("Swiggy banner + Insta story? Live in 10 min").
""",

        "competitor_opened": f"""
COMPETITOR OPENED — New competitor nearby.
Shape: Don't alarm. Frame as: "time to make your position stronger".
Suggest ONE defensive action: more reviews, updated photos, new offer.
Use social proof: "merchants who respond early retain X% of their base".
CTA: binary YES/NO.
""",

        "review_theme_emerged": f"""
REVIEW THEME — A pattern emerged in recent reviews.
Shape: Name the SPECIFIC theme + number of mentions.
If positive: suggest amplifying it (post, GBP highlight).
If negative: suggest ONE specific fix.
Be specific about the quote pattern.
CTA: open_ended.
""",

        "milestone_reached": f"""
MILESTONE — Merchant hit a significant number.
Shape: Celebrate the specific milestone briefly.
Immediately pivot to: "here's the next move to build on this".
Use peer comparison to show where they stand.
CTA: open_ended or binary.
""",

        "dormant_with_vera": f"""
DORMANCY — Merchant hasn't engaged in a while.
Shape: DON'T guilt-trip. Lead with ONE interesting insight about their account.
Make it something they wouldn't know without Vera (derived stat, peer comparison).
Keep it curious and zero-commitment.
CTA: open_ended curiosity question ("Want to see the full breakdown?").
""",

        "curious_ask_due": f"""
CURIOUS ASK — Weekly check-in cadence.
Shape: Ask ONE specific question about their business this week.
Make a SPECIFIC GUESS to make it easier to answer (e.g., "Is it the keratin treatment?").
Offer to turn their answer into something useful immediately.
Keep it very short — under 3 lines.
CTA: open_ended question.
""",

        "renewal_due": f"""
RENEWAL DUE — Subscription expiring soon.
Shape: State exact days remaining.
Frame value in SPECIFIC terms: views generated, leads, calls in last 30 days.
Don't exaggerate — use real numbers from their performance data.
CTA: binary YES/NO.
""",

        "winback_eligible": f"""
WINBACK — Lapsed customer can be re-engaged.
Shape: Reference specific lapse duration.
Suggest a targeted win-back offer from their catalog.
Frame as easy: "I can draft the message for you right now".
CTA: binary YES/NO.
""",

        "customer_lapsed_hard": f"""
CUSTOMER LAPSE — A customer has been gone a long time.
Shape: Warm, NO shame, NO guilt.
Reference their specific goal or service history.
Introduce something NEW that matches their goal.
Remove barriers explicitly ("no commitment", "free trial", "no auto-charge").
CTA: single binary YES with a specific date.
""",

        "supply_alert": f"""
SUPPLY ALERT / COMPLIANCE — Urgent product/compliance issue.
Shape: State the issue with SPECIFIC identifiers (batch numbers, circular number).
Bound the risk clearly ("no safety risk" if applicable).
Derive the count of affected customers from merchant data.
Offer complete workflow (customer message + replacement process).
CTA: open_ended ("Want me to draft X + Y?").
""",

        "chronic_refill_due": f"""
CHRONIC REFILL — Patient's regular medicines are running out.
Shape: Send AS merchant TO customer (merchant_on_behalf).
Name the SPECIFIC medicines (molecule names, not brand).
State exact run-out date.
Show total + savings clearly.
Offer delivery with time window.
Give two-channel option (Reply OR Call) for seniors.
Honor cultural salutation (Namaste for senior customers).
CTA: binary CONFIRM to dispatch.
""",

        "gbp_unverified": f"""
GBP UNVERIFIED — Google Business Profile not verified.
Shape: State exactly what's at stake (missed searches, lower ranking).
Make it specific to their locality.
Offer to walk them through verification (5-10 min process).
CTA: binary YES/NO.
""",

        "cde_opportunity": f"""
CDE OPPORTUNITY — Continuing education/training event available.
Shape: Name the specific event, date, and relevance.
Connect to their practice type or patient mix.
Keep it collegial — peer-to-peer tone.
CTA: open_ended.
""",

    }

    return instructions.get(kind, f"""
{kind.upper()} TRIGGER
Shape: Lead with the specific event/signal that prompted this.
Connect to ONE actionable thing for this merchant.
Use their real numbers and active offers.
Add judgment — interpret what this means for them specifically.
End with ONE clear CTA.
""")


def compose(
    category: dict,
    merchant: dict,
    trigger: dict,
    customer: dict | None = None
) -> dict:
    """
    Main compose function.
    Calls Claude API with the full prompt + few-shot examples.
    Returns: body, cta, send_as, suppression_key, rationale
    """
    prompt = build_prompt(category, merchant, trigger, customer)

    try:
        print(f"[COMPOSE] calling Claude API...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        print(f"[COMPOSE] raw response: {raw[:200]}")

        
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw = part
                    break

        raw = raw.strip()

        result = json.loads(raw)

        return {
            "body": result.get("body", ""),
            "cta": result.get("cta", "open_ended"),
            "send_as": result.get("send_as", "vera"),
            "suppression_key": result.get(
                "suppression_key",
                trigger.get("suppression_key", "")
            ),
            "rationale": result.get("rationale", "")
        }

    except json.JSONDecodeError as e:
        return {
            "body": "",
            "cta": "none",
            "send_as": "vera",
            "suppression_key": trigger.get("suppression_key", ""),
            "rationale": f"JSON parse error: {str(e)}"
        }

    except Exception as e:
        print(f"[COMPOSE ERROR] {str(e)}")
        return {
            "body": "",
            "cta": "none",
            "send_as": "vera",
            "suppression_key": trigger.get("suppression_key", ""),
            "rationale": f"Error: {str(e)}"
            }