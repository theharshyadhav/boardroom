from fastapi import APIRouter, Query
from ..schemas import AskRequest
from .. import narrative

router = APIRouter(prefix="/api", tags=["narrative"])

@router.get("/summary")
async def summary(persona: str = Query("ceo")):
    text = await (narrative.generate_executive_summary() if persona == "ceo" else narrative.generate_persona_narrative(persona))
    return {"persona": persona, "text": text}

@router.get("/boardroom")
async def boardroom():
    return await narrative.generate_boardroom()

@router.post("/ask")
async def ask(req: AskRequest):
    return {"answer": await narrative.answer_question(req.question)}
