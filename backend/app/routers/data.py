from fastapi import APIRouter
from ..evidence_graph import build_source_freshness

router = APIRouter(prefix="/api/data", tags=["data"])

@router.get("/freshness")
def freshness():
    return build_source_freshness()
