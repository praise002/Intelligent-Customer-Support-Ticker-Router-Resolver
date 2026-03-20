import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ZendeskWebhookPayload(BaseModel):
    id: str
    subject: str
    description: str
    status: str
    priority: str
    requester_email: str
    created_at: str


class PlanType(Enum):
    free = "Free"
    premium = "Premium"
    enterprise = "Enterprise"


class Priority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Urgency(Enum):
    high = "High"
    medium = "Medium"
    low = "Low"


class IssueType(Enum):
    account_verification = "Account Verification"
    cards = "cards"
    transfers = "transfers"
    integrations = "integrations"
    fees = "fees"
    account_access = "account_access"
    general = "General"


class RoutingDecision(str, Enum):
    AUTO_RESOLVE = "auto_resolve"
    HUMAN_REVIEW = "human_review"
    ESCALATE = "escalate"


class SupportResponse(BaseModel):
    """Structured response from LLM"""

    response: str = Field(description="Helpful answer to the customer")
    confidence: float = Field(
        description="Confidence score 0.0-1.0 that this resolves the issue",
        ge=0.0,
        le=1.0,
    )


class LLMProvider(str, Enum):
    NVIDIA = "nvidia"
    GROQ = "groq"
    OPENAI = "openai"


class TicketBase(BaseModel):
    ticket_id: int
    subject: str
    content: str
    email: EmailStr
    urgency: Urgency
    issue_type: IssueType


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    retrieval_score: float | None = None
    generated_response: str | None = None
    llm_confidence: float | None = None
    semantic_similarity: float | None = None
    final_confidence: float | None = None
    routing_decision: RoutingDecision | None = None
    judge_tone_empathy: float | None = None
    judge_response_quality: float | None = None
    judge_faithfulness: float | None = None
    judge_groundedness: float | None = None
    judge_overall: float | None = None
    judge_pass: bool | None = None
    judge_reason: str | None = None


class TicketRead(TicketBase):
    id: uuid.UUID
    customer_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    # AI-populated fields
    retrieval_score: float | None
    generated_response: str | None
    llm_confidence: float | None
    semantic_similarity: float | None
    final_confidence: float | None
    routing_decision: RoutingDecision | None
    judge_tone_empathy: float | None = None
    judge_response_quality: float | None = None
    judge_faithfulness: float | None = None
    judge_groundedness: float | None = None
    judge_overall: float | None = None
    judge_pass: bool | None = None
    judge_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)
