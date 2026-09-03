"""
1. SIMULATED DATA SOURCES
Generates 7 realistic business data sources with different refresh cadences,
and deliberately bakes in one coherent, traceable anomaly (a South India
inventory shortage following a monsoon-driven supplier delay) so every
downstream deterministic layer has something real to explain.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, UTC
from .config import settings

REGIONS = ["North India", "South India", "West India", "East India"]
CATEGORIES = ["Home Appliances", "Personal Care", "Electronics Accessories", "Apparel"]
NEW_PRODUCT = "AuraFit Band (New Launch)"

REGION_BASE_UNITS = {"North India": 140, "South India": 160, "West India": 130, "East India": 95}
CATEGORY_MULT = {"Home Appliances": 1.0, "Personal Care": 1.3, "Electronics Accessories": 0.9, "Apparel": 1.1}

TODAY = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
HIST_DAYS = 90
SHORTAGE_START, SHORTAGE_END = 11, 2  # days-ago window of the South India disruption


def _rng():
    return np.random.default_rng(settings.DATA_SEED)


def days_ago(n: int) -> datetime:
    return TODAY - timedelta(days=n)


def generate_all() -> dict:
    rng = _rng()
    sales_rows, inventory_rows, competitor_rows, weather_rows = [], [], [], []

    for i in range(HIST_DAYS, -1, -1):
        date = days_ago(i)
        date_s = date.strftime("%Y-%m-%d")
        weekday = date.weekday()
        weekend_boost = 1.18 if weekday >= 5 else 1.0
        trend = 1 + (HIST_DAYS - i) * 0.0009
        in_shortage = SHORTAGE_END <= i <= SHORTAGE_START

        for region in REGIONS:
            for cat in CATEGORIES:
                base = REGION_BASE_UNITS[region] * CATEGORY_MULT[cat]
                mult = 0.46 if (region == "South India" and in_shortage) else 1.0
                noise = rng.normal(1.0, 0.07)
                units = max(4, round(base * weekend_boost * trend * mult * noise))
                price = round(rng.uniform(699, 2499))
                cost = round(price * rng.uniform(0.58, 0.68))
                sales_rows.append({
                    "date": date_s, "region": region, "category": cat, "product": None,
                    "units": units, "price": price, "revenue": units * price, "cost": units * cost,
                })

        if i <= 8:
            units = round(rng.uniform(18, 60) * (1 + (8 - i) * 0.05))
            price = 1899
            sales_rows.append({
                "date": date_s, "region": "North India", "category": "Electronics Accessories",
                "product": NEW_PRODUCT, "units": units, "price": price,
                "revenue": units * price, "cost": units * round(price * 0.6),
            })

        for region in REGIONS:
            stock_ratio = rng.uniform(0.62, 0.92)
            if region == "South India" and in_shortage:
                stock_ratio = rng.uniform(0.08, 0.22)
            inventory_rows.append({"date": date_s, "region": region, "stock_ratio": round(stock_ratio, 2),
                                    "stockout": stock_ratio < 0.25})

        for region in REGIONS:
            our_price = 1350 + rng.normal(0, 40)
            gap = rng.normal(0.02, 0.03)
            if region == "South India" and 4 <= i <= 14:
                gap = rng.normal(-0.06, 0.02)
            competitor_rows.append({"date": date_s, "region": region, "our_avg_price": round(our_price),
                                     "gap_pct": round(gap * 100, 1)})

        for region in REGIONS:
            rainfall = max(0, rng.normal(8 if region == "South India" else 3, 6))
            if region == "South India" and 8 <= i <= 13:
                rainfall = rng.uniform(55, 95)
            weather_rows.append({"date": date_s, "region": region, "rainfall_mm": round(rainfall),
                                  "disruption": rainfall > 45})

    marketing_rows = []
    campaign_by_region = {
        "North India": "Festive Value Push",
        "South India": "South Metro Reach",
        "West India": "Prime Time Bundles",
        "East India": "AuraFit Launch Blitz",
    }
    for w in range(11, -1, -1):
        w_date = days_ago(w * 7).strftime("%Y-%m-%d")
        for region in REGIONS:
            camp = campaign_by_region[region]
            spend = round(rng.uniform(180000, 420000))
            impressions = round(spend * rng.uniform(9, 13))
            click_rate = rng.uniform(0.018, 0.034)
            conv_rate = rng.uniform(0.06, 0.11)
            if camp == "South Metro Reach" and w <= 2:
                conv_rate *= 0.58
            clicks = round(impressions * click_rate)
            conversions = round(clicks * conv_rate)
            marketing_rows.append({"week_of": w_date, "region": region, "campaign": camp, "spend": spend,
                                    "impressions": impressions, "clicks": clicks, "conversions": conversions,
                                    "conv_rate": round(conv_rate * 100, 2)})

    review_templates = {
        "pos": ["Great build quality and fast delivery.", "Works exactly as advertised, very happy.",
                "Customer support resolved my issue quickly.", "Value for money, would buy again.",
                "Packaging was excellent and product arrived safely."],
        "neu": ["Product is okay, does the job.", "Delivery took a bit longer than expected.",
                "Average experience, nothing special.", "Matches description, no complaints."],
        "neg": ["Item was out of stock for weeks, frustrating.", "Delivery delayed due to supplier issues in Chennai.",
                "Not satisfied with the quality for the price.", "Had to wait too long for replenishment.",
                "Support was slow to respond to my query."],
    }
    review_rows = []
    for i in range(59, -1, -1):
        date_s = days_ago(i).strftime("%Y-%m-%d")
        n = rng.integers(4, 9)
        for _ in range(n):
            region = rng.choice(REGIONS)
            bucket = "pos" if rng.random() < 0.62 else ("neu" if rng.random() < 0.6 else "neg")
            if region == "South India" and (SHORTAGE_END - 1) <= i <= SHORTAGE_START and rng.random() < 0.65:
                bucket = "neg"
            score = {"pos": rng.integers(80, 101), "neu": rng.integers(55, 76), "neg": rng.integers(15, 46)}[bucket]
            review_rows.append({"date": date_s, "region": str(region), "sentiment": bucket, "score": int(score),
                                 "text": str(rng.choice(review_templates[bucket]))})

    news_rows = [
        {"date": days_ago(13).strftime("%Y-%m-%d"), "region": "South India", "tag": "weather",
         "headline": "Heavy monsoon rainfall disrupts logistics hubs across Chennai and Coimbatore."},
        {"date": days_ago(12).strftime("%Y-%m-%d"), "region": "South India", "tag": "supply-chain",
         "headline": "Key regional supplier reports 6-day dispatch delay following warehouse flooding."},
        {"date": days_ago(10).strftime("%Y-%m-%d"), "region": "South India", "tag": "supply-chain",
         "headline": "Distribution centers in South India report stockouts across appliance and accessory lines."},
        {"date": days_ago(9).strftime("%Y-%m-%d"), "region": "South India", "tag": "competitor",
         "headline": "Regional competitor launches aggressive discount pricing during the supply gap."},
        {"date": days_ago(6).strftime("%Y-%m-%d"), "region": None, "tag": "industry",
         "headline": "Festive-season e-commerce demand up 14% YoY across category, industry report shows."},
        {"date": days_ago(4).strftime("%Y-%m-%d"), "region": "South India", "tag": "supply-chain",
         "headline": "Supplier resumes partial dispatch; full recovery expected within two weeks."},
        {"date": days_ago(2).strftime("%Y-%m-%d"), "region": None, "tag": "launch",
         "headline": "AuraFit Band launch sees early traction in North India, limited data so far."},
    ]

    return {
        "sales": pd.DataFrame(sales_rows),
        "inventory": pd.DataFrame(inventory_rows),
        "marketing": pd.DataFrame(marketing_rows),
        "reviews": pd.DataFrame(review_rows),
        "competitor": pd.DataFrame(competitor_rows),
        "weather": pd.DataFrame(weather_rows),
        "news": pd.DataFrame(news_rows),
    }


# Module-level cache: generated once per process (deterministic seed => same
# dataset every run, which is what makes the demo narrative reproducible).
_CACHE = None

def get_data() -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = generate_all()
    return _CACHE
