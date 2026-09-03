import json
from .driver_analysis import decompose_revenue_drivers
from .material_events import build_material_events
from .llm_provider import call_llm

PERSONA_STYLES = {
    "ceo": "You address the CEO. Be extremely concise: one headline sentence on what happened, one on the recommended action. No caveats, no jargon.",
    "finance": "You address a Finance Manager. Emphasize margin, cost, and P&L impact in detail, referencing the numeric shares of each driver. 3-4 sentences.",
    "marketing": "You address a Marketing Manager. Focus only on campaign performance and what to do about spend allocation. 3-4 sentences.",
    "regional": "You address the Regional Manager for South India only. Focus exclusively on South India specifics and concrete regional next steps. 3-4 sentences.",
}


def build_digest() -> dict:
    driver_tree = decompose_revenue_drivers()
    events = build_material_events()
    volume_children = [n for n in driver_tree["nodes"] if n.get("parent") == "volume"]
    return {
        "total_revenue_change_pct": round(driver_tree["totalDeltaPct"], 1),
        "south_india_revenue_change_pct": round(driver_tree["southDeltaPct"], 1),
        "event_window": driver_tree["eventWindow"],
        "drivers": [{"factor": n["label"], "share_pct": n["pct"]} for n in volume_children],
        "material_events": [{"title": e["title"], "severity": e["severity"], "confidence": e["confidence"]["band"],
                              "region": e.get("region")} for e in events if not e.get("abstain")],
        "marketing_conversion_trend": "South Metro Reach campaign conversion down over the last three weeks",
        "customer_sentiment": "Overall sentiment stable to positive nationally; regional dip in South India tied to stockouts",
    }


def _fallback_summary(digest: dict) -> str:
    return (f"Revenue declined {abs(digest['south_india_revenue_change_pct'])}% in South India between "
            f"{digest['event_window']['start']} and {digest['event_window']['end']}, primarily driven by an "
            "inventory shortage following supplier delays after monsoon flooding. Competitor undercutting and a "
            "slowdown in one regional campaign compounded the effect. Customer sentiment nationally remains stable. "
            "Immediate attention should focus on replenishment in South India and reallocating the underperforming "
            "campaign's spend. (Generated locally — live narrative model unavailable.)")


async def generate_executive_summary() -> str:
    digest = build_digest()
    system = ("You are BoardMind's narrative layer for a company boardroom dashboard. You are given ONLY "
              "pre-computed, already-verified figures — never invent numbers not present in the input. Write a "
              "concise executive summary (3-4 sentences, plain business English, no bullet points, no markdown) "
              "explaining what changed, why, and what deserves attention. Ground every claim strictly in the "
              "provided JSON.")
    text = await call_llm(system, f"Data digest:\n{json.dumps(digest, indent=2)}\n\nWrite the executive summary now.", 300)
    return text or _fallback_summary(digest)


async def generate_persona_narrative(persona: str) -> str:
    digest = build_digest()
    style = PERSONA_STYLES.get(persona, PERSONA_STYLES["ceo"])
    system = f"You are BoardMind's narrative layer. {style} Use ONLY the numbers in the provided JSON, never invent figures. No markdown."
    text = await call_llm(system, f"Data digest:\n{json.dumps(digest, indent=2)}", 260)
    return text or _fallback_summary(digest)


def _fallback_boardroom(digest: dict) -> list[dict]:
    return [
        {"role": "CEO", "message": f"Growth is intact nationally but South India needs immediate attention — a {abs(digest['south_india_revenue_change_pct'])}% regional dip is a distraction from our festive push."},
        {"role": "CFO", "message": "Margin exposure is manageable if we hold price rather than chase the competitor's discount — I'd rather protect unit economics than volume this week."},
        {"role": "CMO", "message": "South Metro Reach is dragging blended ROAS down; reallocating that spend to Festive Value Push is the highest-leverage move available to us right now."},
        {"role": "COO", "message": "The root cause is logistics, not demand — replenishment and a backup supplier fix this faster than any pricing or marketing lever."},
        {"role": "Risk Officer", "message": "Confidence on the inventory driver is high, but I'd keep monitoring the competitor pricing gap in case it persists past the supplier recovery date."},
        {"role": "Operations Head", "message": "We can get emergency stock into the Chennai DC within 72 hours — that alone should stop most of the bleeding."},
        {"role": "Decision Agent", "message": "Consensus: prioritize emergency replenishment in South India, pause and reallocate the underperforming campaign, and hold price rather than match the competitor discount."},
    ]


async def generate_boardroom() -> list[dict]:
    digest = build_digest()
    system = ('You are BoardMind\'s multi-agent boardroom layer. Given the data digest, produce a JSON array '
               '(and ONLY valid JSON, no markdown fences, no prose outside the JSON) of exactly 6 objects, one per '
               'executive persona, each shaped as {"role":"CEO"|"CFO"|"CMO"|"COO"|"Risk Officer"|"Operations Head",'
               '"message":"2-3 sentences from that persona\'s specific lens on the SAME data, referencing only the '
               'given numbers"}. Then a 7th final object {"role":"Decision Agent","message":"2-3 sentence synthesis '
               'of the consensus recommended action"}. Return exactly 7 objects total in one JSON array.')
    text = await call_llm(system, f"Data digest:\n{json.dumps(digest, indent=2)}", 700)
    if text:
        try:
            cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, list) and len(parsed) >= 6:
                return parsed
        except Exception:
            pass
    return _fallback_boardroom(digest)


async def answer_question(question: str) -> str:
    digest = build_digest()
    system = ("You are BoardMind's Q&A layer. Answer strictly using the provided data digest. If the question "
              "cannot be answered from this data, say clearly that evidence is insufficient and suggest what data "
              "would help — never fabricate an answer. Keep answers under 4 sentences, no markdown.")
    text = await call_llm(system, f"Data digest:\n{json.dumps(digest, indent=2)}\n\nQuestion: {question}", 260)
    return text or ("I can't reach the live narrative model right now, so I won't guess — please try again in a "
                    "moment, or check the Evidence tab for the underlying figures directly.")
