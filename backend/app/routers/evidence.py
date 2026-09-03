from fastapi import APIRouter
from ..evidence_graph import build_source_freshness, build_graph, graph_to_reactflow
from ..material_events import build_material_events

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

@router.get("/sources")
def sources():
    return build_source_freshness()

@router.get("/insights")
def insights():
    return build_material_events()

@router.get("/graph")
def graph():
    events = build_material_events()
    g = build_graph(events)
    return graph_to_reactflow(g)
