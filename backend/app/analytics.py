"""
2+3. HARMONIZATION + SEMANTIC KPI LAYER  (DuckDB / SQL — no model calls)
4. MATERIAL CHANGE DETECTION            (statistics — no model calls)
"""
import duckdb
import numpy as np
import pandas as pd
from .data_gen import get_data, TODAY, HIST_DAYS, days_ago
from .config import settings


def _con():
    con = duckdb.connect(settings.DUCKDB_PATH)
    data = get_data()
    con.register("sales", data["sales"])
    con.register("inventory", data["inventory"])
    con.register("reviews", data["reviews"])
    return con


def build_kpi_series(region: str | None = None) -> dict:
    """Semantic KPI layer: harmonizes raw sales/inventory/review rows into a
    clean daily KPI series entirely via SQL aggregation — this is the
    deterministic 'SQL / rules' layer required by the brief."""
    con = _con()
    where = f"WHERE region = '{region}'" if region else ""

    rev = con.execute(f"""
        SELECT date, SUM(revenue) AS revenue, SUM(cost) AS cost, SUM(units) AS orders
        FROM sales {where} GROUP BY date ORDER BY date
    """).df()

    inv = con.execute(f"""
        SELECT date, AVG(stock_ratio) AS stock_ratio
        FROM inventory {where} GROUP BY date ORDER BY date
    """).df()

    csat = con.execute(f"""
        SELECT date, AVG(score) AS score
        FROM reviews {where} GROUP BY date ORDER BY date
    """).df()
    con.close()

    dates = [days_ago(i).strftime("%Y-%m-%d") for i in range(HIST_DAYS, -1, -1)]
    idx = pd.DataFrame({"date": dates})

    rev = idx.merge(rev, on="date", how="left").fillna(0)
    inv = idx.merge(inv, on="date", how="left")
    inv["stock_ratio"] = inv["stock_ratio"].fillna(0.7)
    csat = idx.merge(csat, on="date", how="left")
    csat["score"] = csat["score"].ffill().fillna(70)
    # 5-day rolling smoothing for the sentiment index (a semantic-KPI rollup, not raw counts)
    csat["score_smooth"] = csat["score"].rolling(5, min_periods=1).mean()

    return {
        "dates": dates,
        "revenue": rev["revenue"].round().astype(int).tolist(),
        "profit": (rev["revenue"] - rev["cost"]).round().astype(int).tolist(),
        "orders": rev["orders"].round().astype(int).tolist(),
        "invHealth": (inv["stock_ratio"] * 100).round().astype(int).tolist(),
        "csat": csat["score_smooth"].round().astype(int).tolist(),
    }


def pct_change_window(series: list[float], window: int = 7) -> dict:
    s = np.array(series, dtype=float)
    recent = s[-window:].sum()
    prior = s[-window * 2:-window].sum()
    pct = ((recent - prior) / prior * 100) if prior else 0.0
    return {"recent": float(recent), "prior": float(prior), "pct": float(pct)}


def z_score_of_window_change(series: list[float], window: int = 7) -> float:
    """Materiality score: how many standard deviations of *historical daily
    volatility* does this window's change represent? Pure statistics."""
    s = np.array(series, dtype=float)
    pct = pct_change_window(series, window)["pct"]
    history = s[:-window]
    daily_pct = np.diff(history) / np.where(history[:-1] == 0, 1, history[:-1])
    vol = np.std(daily_pct) * np.sqrt(window) * 100
    return float(pct / vol) if vol else 0.0


def scan_worst_window(dates: list[str], series: list[float], window: int = 7, scan: int = 14) -> dict | None:
    """A fixed 'yesterday vs the day before' comparison is fragile: whatever
    anomaly exists in the data can straddle that exact boundary depending on
    what day this happens to be run, diluting or hiding it. Real anomaly
    detection scans a range of recent windows and surfaces the most extreme
    one, scored against the *empirical distribution* of that same window
    comparison across history (not a daily-volatility approximation, which
    under-weights weekly seasonality). This is what makes material-event
    detection reliable regardless of when the demo is presented, and it
    reports the actual date range of the event rather than a vague 'last week'."""
    s = np.array(series, dtype=float)
    n = len(s)
    if n < 4 * window + scan:
        return None

    # empirical distribution of window-over-prior-window % change across all history
    pct_series = []
    for end in range(2 * window, n + 1):
        recent, prior = s[end - window:end], s[end - 2 * window:end - window]
        pct_series.append(((recent.sum() - prior.sum()) / prior.sum() * 100) if prior.sum() else 0.0)
    pct_series = np.array(pct_series)  # index j corresponds to end = j + 2*window

    baseline = pct_series[:-scan] if len(pct_series) > scan else pct_series
    mean_b, std_b = float(baseline.mean()), float(baseline.std())

    best = None
    for offset in range(0, scan):
        end = n - offset
        j = end - 2 * window
        if j < 0 or j >= len(pct_series):
            continue
        pct = float(pct_series[j])
        z = (pct - mean_b) / std_b if std_b else 0.0
        if best is None or abs(z) > abs(best["z"]):
            best = {"offset": offset, "pct": pct, "z": float(z),
                    "start_date": dates[end - window], "end_date": dates[end - 1]}
    return best


def materiality_band(z: float) -> str:
    az = abs(z)
    if az >= 3:
        return "critical"
    if az >= 2:
        return "high"
    if az >= 1:
        return "medium"
    return "low"
