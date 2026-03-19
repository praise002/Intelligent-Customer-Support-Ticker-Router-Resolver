from enum import Enum

from pydantic import BaseModel, EmailStr, Field


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


class Urgency(Enum):
    high = "High"
    medium = "Medium"
    low = "Low"


class IssueType(Enum):
    billing = "Billing"
    technical = "Technical"
    account = "Account"
    feature = "Feature"
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


# TODO: FOR CUSTOMER AND TICKET