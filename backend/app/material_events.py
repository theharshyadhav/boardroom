from .data_gen import get_data, NEW_PRODUCT
from .analytics import build_kpi_series, materiality_band
from .driver_analysis import decompose_revenue_drivers
from .evidence_graph import build_source_freshness
from .confidence import confidence_score


def build_material_events() -> list[dict]:
    data = get_data()
    driver_tree = decompose_revenue_drivers()
    sources = {s["id"]: s for s in build_source_freshness()}
    events = []

    band = materiality_band(driver_tree["southZ"])
    conf = confidence_score(
        freshness_mins=sources["inventory"]["freshnessMins"], expected_cadence_mins=60,
        history_days=90, expected_history_days=90, missing_rate=0.02, signals_agree=0.92, evidence_count=5,
    )
    events.append({
        "id": "evt_revenue_drop",
        "title": f"Revenue in South India declined {abs(driver_tree['southDeltaPct']):.1f}%",
        "severity": band, "kpi": "revenue", "region": "South India",
        "body": (f"Revenue fell {abs(driver_tree['southDeltaPct']):.1f}% in South India between "
                 f"{driver_tree['eventWindow']['start']} and {driver_tree['eventWindow']['end']}, "
                 "following an inventory shortage. Independent signals (inventory, competitor pricing, "
                 "weather, reviews, news) corroborate the same window."),
        "sources": ["sales", "inventory", "competitor", "weather", "reviews", "news"],
        "confidence": conf, "z": driver_tree["southZ"], "eventWindow": driver_tree["eventWindow"],
    })

    camp_conf = confidence_score(sources["marketing"]["freshnessMins"], 10080, 84, 84, 0.04, 0.7, 3)
    events.append({
        "id": "evt_campaign", "title": "South Metro Reach campaign conversion down sharply",
        "severity": "medium", "kpi": "marketing", "region": "South India",
        "body": "Conversion rate on the South Metro Reach campaign fell over the last three weeks, "
                "compounding the regional revenue impact alongside the supply disruption.",
        "sources": ["marketing"], "confidence": camp_conf,
    })

    wx_conf = confidence_score(sources["weather"]["freshnessMins"], 1440, 90, 90, 0.0, 0.6, 2)
    events.append({
        "id": "evt_weather", "title": "Monsoon disruption in South India logistics hubs",
        "severity": "low", "kpi": "inventory", "region": "South India",
        "body": "Elevated rainfall around Chennai and Coimbatore coincided with the supplier dispatch "
                "delay, a contributing but secondary factor.",
        "sources": ["weather", "news"], "confidence": wx_conf,
    })

    np_sales = data["sales"][data["sales"]["product"] == NEW_PRODUCT]
    history_days = np_sales.date.nunique() if len(np_sales) else 0
    np_conf = confidence_score(20, 1440, history_days, 90, 0.35, 0.4, 1)
    events.append({
        "id": "evt_new_product", "title": "AuraFit Band — insufficient history to explain early trend",
        "severity": "low", "kpi": "new_product", "region": "North India",
        "body": (f"Only {history_days} days of sales history exist for this launch. The system "
                 "intentionally withholds a causal explanation until more data accrues."),
        "sources": ["sales"], "confidence": np_conf, "abstain": True,
    })

    return events
