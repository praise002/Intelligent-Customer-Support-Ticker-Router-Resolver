import uuid
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

SUCCESS_EXAMPLE = "success"
FAILURE_EXAMPLE = "failure"


class ZendeskWebhookPayload(BaseModel):
    id: str
    subject: str
    description: str
    status: str
    priority: str
    requester_email: str
    created_at: str


class PlanType(str, Enum):
    free = "Free"
    premium = "Premium"
    enterprise = "Enterprise"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Urgency(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Status(Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    blocked = "blocked"


class IssueType(str, Enum):
    account_verification = "account_verification"
    cards = "cards"
    transfers = "transfers"
    integrations = "integrations"
    fees = "fees"
    account_access = "account_access"
    technical = "technical"
    general = "general"


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


class WebFormTicket(BaseModel):
    """Schema for web form submissions"""

    ticket_id: int | None = None
    subject: str
    content: str
    email: EmailStr
    name: str | None = None


class TicketBase(BaseModel):
    ticket_id: int
    subject: str
    content: str
    email: EmailStr


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    urgency: Urgency | None = None
    issue_type: IssueType | None = None
    status: Status | None = None
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


class TicketResponseData(TicketBase):
    id: uuid.UUID
    customer_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    name: str | None = None

    # AI-populated fields
    urgency: Urgency | None = None
    issue_type: IssueType | None = None
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


class TicketResponse(BaseModel):
    status: str
    message: str
    data: list[TicketResponseData]


class TicketClassification(BaseModel):
    issue_type: Literal[
        "account_verification",
        "cards",
        "transfers",
        "integrations",
        "fees",
        "account_access",
        "technical",
        "general",
    ]
    urgency: Literal["high", "medium", "low"]
    reasoning: str
