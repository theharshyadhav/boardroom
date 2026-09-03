from fastapi import APIRouter
from ..recommendations import build_recommendations
from .. import feedback as feedback_store

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

@router.get("")
def get_recommendations():
    recs = build_recommendations()
    for r in recs:
        r["feedbackStats"] = feedback_store.get_stats(r["id"])
    return recs
