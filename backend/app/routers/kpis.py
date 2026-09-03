from fastapi import APIRouter, Query
from typing import Optional
from ..analytics import build_kpi_series, scan_worst_window, materiality_band, pct_change_window

router = APIRouter(prefix="/api/kpis", tags=["kpis"])

@router.get("")
def get_kpis(region: Optional[str] = Query(None)):
    series = build_kpi_series(region)
    out = {"dates": series["dates"], "series": {}}
    for metric in ["revenue", "profit", "orders", "invHealth", "csat"]:
        values = series[metric]
        window = scan_worst_window(series["dates"], values, window=7, scan=14) or {}
        live = pct_change_window(values, 7)
        out["series"][metric] = {
            "values": values,
            "latest": values[-1] if values else 0,
            "liveDeltaPct": round(live["pct"], 1),
            "materialWindow": window,
            "materialityBand": materiality_band(window.get("z", 0)) if window else "low",
        }
    return out
