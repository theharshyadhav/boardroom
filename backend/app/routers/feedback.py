from fastapi import APIRouter, HTTPException
from ..schemas import FeedbackRequest
from .. import feedback as feedback_store

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

@router.get("/{rec_id}")
def get_feedback(rec_id: str):
    return feedback_store.get_stats(rec_id)

@router.post("")
def post_feedback(req: FeedbackRequest):
    try:
        return feedback_store.submit_feedback(req.recId, req.action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("")
def reset_feedback():
    feedback_store.reset_all()
    return {"ok": True}
