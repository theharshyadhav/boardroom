from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    role: str

class SimulateRequest(BaseModel):
    priceChangePct: float = 0
    marketingSpendPct: float = 0
    inventoryInvestPct: float = 0
    supplierSwitch: bool = False

class FeedbackRequest(BaseModel):
    recId: str
    action: str  # "accepted" | "rejected" | "modified"

class AskRequest(BaseModel):
    question: str

class AgentRunRequest(BaseModel):
    role: str

class AlertAckRequest(BaseModel):
    alertId: str
