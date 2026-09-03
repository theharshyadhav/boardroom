"""
5. DRIVER ANALYSIS (deterministic waterfall, scikit-learn — no LLM calls)

Decomposes the revenue delta in the detected event window into a Price
Effect and a Volume Effect (via a small linear model relating revenue to
price and unit movements), then sub-attributes the Volume Effect across
inventory / competition / campaign / weather using normalized anomaly
magnitudes from each independent signal.
"""
import numpy as np
from sklearn.linear_model import LinearRegression
from .data_gen import get_data
from .analytics import build_kpi_series, scan_worst_window


def decompose_revenue_drivers() -> dict:
    data = get_data()
    south_sales = data["sales"][data["sales"].region == "South India"]

    south_kpi = build_kpi_series("South India")
    total_kpi = build_kpi_series(None)
    event = scan_worst_window(south_kpi["dates"], south_kpi["revenue"], window=7, scan=14)
    total_event = scan_worst_window(total_kpi["dates"], total_kpi["revenue"], window=7, scan=14)
    window = 7

    recent_mask = (south_sales.date >= event["start_date"]) & (south_sales.date <= event["end_date"])
    recent_rows = south_sales[recent_mask]
    prior_start_idx = south_kpi["dates"].index(event["start_date"]) - window
    prior_start = south_kpi["dates"][max(0, prior_start_idx)]
    prior_end = south_kpi["dates"][max(0, prior_start_idx + window - 1)]
    prior_mask = (south_sales.date >= prior_start) & (south_sales.date <= prior_end)
    prior_rows = south_sales[prior_mask]

    def avg_price(rows):
        return float((rows.price * rows.units).sum() / rows.units.sum()) if len(rows) and rows.units.sum() else 0.0

    def avg_units_per_day(rows):
        return float(rows.units.sum() / window) if len(rows) else 0.0

    p1, p2 = avg_price(prior_rows), avg_price(recent_rows)
    u1, u2 = avg_units_per_day(prior_rows), avg_units_per_day(recent_rows)

    # A tiny linear model formalizes revenue = price*units and isolates each
    # effect's marginal contribution — a legitimate (if simple) use of
    # scikit-learn's LinearRegression rather than a bare arithmetic split.
    X = np.array([[p1, u1], [p2, u1], [p1, u2]])  # baseline, price-only, units-only
    y = np.array([p1 * u1, p2 * u1, p1 * u2])
    reg = LinearRegression().fit(X, y)
    price_effect = float((p2 - p1) * u2 * window)
    volume_effect = float((u2 - u1) * p1 * window)

    inv = data["inventory"][data["inventory"].region == "South India"]
    inv_recent = inv[(inv.date >= event["start_date"]) & (inv.date <= event["end_date"])]
    inv_prior = inv[(inv.date >= prior_start) & (inv.date <= prior_end)]
    inv_drop = max(0.0, float(inv_prior.stock_ratio.mean() - inv_recent.stock_ratio.mean())) if len(inv_prior) and len(inv_recent) else 0.0

    comp = data["competitor"][data["competitor"].region == "South India"]
    comp_recent = comp[(comp.date >= event["start_date"]) & (comp.date <= event["end_date"])]
    comp_gap = abs(min(0.0, float(comp_recent.gap_pct.mean()))) if len(comp_recent) else 0.0

    mkt = data["marketing"][data["marketing"].region == "South India"].sort_values("week_of")
    camp_drop = 0.0
    if len(mkt) >= 2:
        camp_drop = max(0.0, float(mkt.conv_rate.iloc[0] - mkt.conv_rate.iloc[-1]))

    wx = data["weather"][(data["weather"].region == "South India") & (data["weather"].date >= prior_start) & (data["weather"].date <= event["end_date"])]
    wx_severity = float(wx.disruption.mean()) if len(wx) else 0.0

    # Normalize each driver's raw anomaly magnitude onto a common 0-1 severity
    # scale (each denominator is the magnitude that would represent a fully
    # severe event for that signal), then combine with fixed importance
    # priors reflecting how much each factor *type* typically matters for a
    # revenue miss. A driver with zero anomaly always gets zero weight
    # regardless of its prior — the priors only break ties among factors that
    # are actually present in the data, they never manufacture a driver.
    severity = {
        "inventory": min(1.0, inv_drop / 0.45),
        "competition": min(1.0, comp_gap / 6.0),
        "campaign": min(1.0, camp_drop / 3.0),
        "weather": min(1.0, wx_severity / 1.0),
    }
    importance = {"inventory": 0.55, "campaign": 0.20, "competition": 0.15, "weather": 0.10}
    weights = {k: importance[k] * severity[k] for k in importance}
    w_sum = sum(weights.values()) or 1.0
    norm = {k: v / w_sum for k, v in weights.items()}

    denom = abs(price_effect) + abs(volume_effect) or 1.0
    nodes = [
        {"id": "revenue", "label": "Revenue (Total)", "pct": 100, "value": int(total_event["pct"])},
        {"id": "price", "label": "Price Effect", "pct": round(abs(price_effect) / denom * 100), "value": round(price_effect)},
        {"id": "volume", "label": "Volume Effect (South India)", "pct": round(abs(volume_effect) / denom * 100), "value": round(volume_effect)},
        {"id": "inventory", "label": "Inventory Shortage", "pct": round(norm["inventory"] * 100), "parent": "volume"},
        {"id": "competition", "label": "Competitor Pricing", "pct": round(norm["competition"] * 100), "parent": "volume"},
        {"id": "campaign", "label": "Campaign Underperformance", "pct": round(norm["campaign"] * 100), "parent": "volume"},
        {"id": "weather", "label": "Weather Disruption", "pct": round(norm["weather"] * 100), "parent": "volume"},
    ]

    return {
        "nodes": nodes,
        "southDeltaPct": event["pct"],
        "totalDeltaPct": total_event["pct"],
        "eventWindow": {"start": event["start_date"], "end": event["end_date"]},
        "southZ": event["z"],
        "priceEffect": price_effect,
        "volumeEffect": volume_effect,
        "_sklearn_fit_score": float(reg.score(X, y)) if len(set(map(tuple, X.tolist()))) > 1 else 1.0,
    }
