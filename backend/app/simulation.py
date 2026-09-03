"""
9. SIMULATION ENGINE (deterministic formulas — no LLM calls)
"""

def run_simulation(base: dict, price_change_pct: float, marketing_spend_pct: float,
                    inventory_invest_pct: float, supplier_switch: bool) -> dict:
    price_change = price_change_pct / 100
    elasticity = -1.35
    volume_from_price = elasticity * price_change

    spend_change = marketing_spend_pct / 100
    sign = 1 if spend_change > 0 else (-1 if spend_change < 0 else 0)
    volume_from_marketing = sign * (abs(spend_change) ** 0.5) * 0.22

    inv_invest = inventory_invest_pct / 100
    stockout_recovery_frac = min(0.9, max(0.0, inv_invest * 1.1))
    volume_from_inventory = stockout_recovery_frac * 0.14

    supplier_bonus = 0.05 if supplier_switch else 0.0

    total_volume_change = volume_from_price + volume_from_marketing + volume_from_inventory + supplier_bonus
    revenue_multiplier = (1 + price_change) * (1 + total_volume_change)

    new_revenue = base["revenue"] * revenue_multiplier
    margin_base = 0.35
    margin_change = price_change * 0.6 - max(0.0, spend_change) * 0.03 - (0.015 if supplier_switch else 0.0)
    new_margin = min(0.6, max(0.15, margin_base + margin_change))
    new_profit = new_revenue * new_margin
    new_orders = base["orders"] * (1 + total_volume_change)
    new_inv_health = min(100.0, base["invHealth"] + stockout_recovery_frac * 45 - (0 if supplier_switch else 2))
    risk_base = 48
    new_risk = max(5.0, risk_base - stockout_recovery_frac * 30 + max(0.0, -spend_change) * 20
                   - (10 if supplier_switch else 0) + abs(price_change) * 15)
    new_csat = min(100.0, base["csat"] + stockout_recovery_frac * 8 - max(0.0, price_change) * 10
                   + max(0.0, spend_change) * 3)

    return {
        "revenue": round(new_revenue), "profit": round(new_profit), "orders": round(new_orders),
        "invHealth": round(new_inv_health), "risk": round(new_risk), "csat": round(new_csat),
    }
