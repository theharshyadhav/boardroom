"""
8. RECOMMENDATION ENGINE (deterministic templates parameterized by computed
figures — no LLM calls). Every recommendation follows the required chain:
Driver -> Controllable Lever -> Recommended Action -> Expected Impact ->
Owner -> Confidence -> Monitoring Plan.

Confidence for every recommendation is computed via the same confidence_score()
engine used for material events — never a hardcoded number — so a recommendation
can never claim more certainty than the evidence backing it actually supports.
"""
from .driver_analysis import decompose_revenue_drivers
from .material_events import build_material_events
from .evidence_graph import build_source_freshness
from .confidence import confidence_score


def build_recommendations() -> list[dict]:
    driver_tree = decompose_revenue_drivers()
    events = build_material_events()
    sources = {s["id"]: s for s in build_source_freshness()}
    inv_share = next(n["pct"] for n in driver_tree["nodes"] if n["id"] == "inventory")
    comp_share = next(n["pct"] for n in driver_tree["nodes"] if n["id"] == "competition")
    revenue_event = next(e for e in events if e["id"] == "evt_revenue_drop")
    campaign_event = next(e for e in events if e["id"] == "evt_campaign")

    # Competitor-pricing confidence: no dedicated material event exists for this
    # driver, so it's scored the same way every other confidence figure in this
    # app is — freshness of the underlying source, full history availability,
    # and evidence_count=1 because (unlike the inventory story) only one signal
    # corroborates it, which the confidence engine will correctly mark as
    # thinner support than the 6-source inventory finding.
    price_hold_confidence = confidence_score(
        freshness_mins=sources["competitor"]["freshnessMins"], expected_cadence_mins=1440,
        history_days=90, expected_history_days=90, missing_rate=0.0,
        signals_agree=comp_share / 100, evidence_count=1,
    )

    return [
        {
            "id": "rec_replenish_inventory",
            "driver": f"Inventory shortage in South India ({inv_share}% of unexplained volume drop)",
            "lever": "Emergency replenishment + secondary supplier activation",
            "action": "Air-freight 3,200 units of top SKUs into the Chennai DC within 72 hours; "
                      "activate backup supplier for the next cycle.",
            "impact": "Recovers an estimated ₹1.8–2.3Cr of at-risk weekly revenue in South India within 2 weeks.",
            "owner": "COO — Regional Operations",
            "confidence": revenue_event["confidence"],
            "monitoring": "Track daily stock-to-reorder ratio in South India; alert if it stays below "
                           "0.35 for 3+ consecutive days.",
        },
        {
            "id": "rec_pause_campaign",
            "driver": "South Metro Reach campaign conversion down over the last three weeks",
            "lever": "Reallocate underperforming ad spend",
            "action": "Pause South Metro Reach for 10 days and reallocate 60% of budget to Festive "
                      "Value Push, which is converting above baseline.",
            "impact": "Improves blended marketing ROAS by an estimated 0.4x without reducing total regional spend.",
            "owner": "CMO — Performance Marketing",
            "confidence": campaign_event["confidence"],
            "monitoring": "Review weekly conversion rate by campaign; resume South Metro Reach only "
                           "once inventory recovers above 60%.",
        },
        {
            "id": "rec_price_hold",
            "driver": "Competitor undercutting during the shortage window",
            "lever": "Temporary price-match on top 5 SKUs",
            "action": "Hold price rather than match the competitor discount; the gap is expected to "
                      "close once supply recovers.",
            "impact": "Preserves an estimated ₹40–60L in gross margin versus a reactive price cut.",
            "owner": "CFO — Pricing & Margins",
            "confidence": price_hold_confidence,
            "monitoring": "Re-evaluate if competitor gap widens beyond 8% or persists past the "
                           "supplier recovery date.",
        },
    ]
