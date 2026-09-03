from fastapi import APIRouter, Query
from typing import Optional
from ..schemas import SimulateRequest
from ..analytics import build_kpi_series
from ..simulation import run_simulation

router = APIRouter(prefix="/api/simulate", tags=["simulate"])

@router.post("")
def simulate(req: SimulateRequest, region: Optional[str] = Query(None)):
    series = build_kpi_series(region)
    base = {
        "revenue": sum(series["revenue"][-7:]),
        "profit": sum(series["profit"][-7:]),
        "orders": sum(series["orders"][-7:]),
        "invHealth": series["invHealth"][-1],
        "csat": series["csat"][-1],
    }
    result = run_simulation(base, req.priceChangePct, req.marketingSpendPct, req.inventoryInvestPct, req.supplierSwitch)
    return {"base": base, "result": result}
