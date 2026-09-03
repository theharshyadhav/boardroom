from fastapi import APIRouter, Query
from typing import Optional
from ..material_events import build_material_events

router = APIRouter(prefix="/api/events", tags=["events"])

@router.get("")
def get_events(region: Optional[str] = Query(None)):
    events = build_material_events()
    if region:
        events = [e for e in events if not e.get("region") or e["region"] == region]
    return events
