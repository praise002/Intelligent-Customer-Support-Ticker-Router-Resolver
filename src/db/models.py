import uuid
from datetime import datetime
from typing import Optional

from pydantic import EmailStr
from sqlalchemy import DateTime, String, func
from sqlmodel import Column, Field, Relationship, SQLModel

from src.tickets.schemas import IssueType, PlanType, RoutingDecision, Urgency


class Customer(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    first_name: str = Field(max_length=50, min_length=1)
    last_name: str = Field(max_length=50, min_length=1)
    email: EmailStr = Field(
        sa_column=Column(String(50), nullable=False, unique=True), min_length=1
    )

    plan_type: PlanType = Field(default=PlanType.free)

    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),  # Database-side default
            onupdate=func.now(),
            nullable=False,
        ),
    )
    tickets: list["Ticket"] = Relationship(
        back_populates="customer",
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return self.full_name


class Ticket(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ticket_id: int
    name: str | None = None
    subject: str
    content: str
    email: EmailStr
    urgency: Urgency | None = None
    issue_type: IssueType | None = None

    customer_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="customer.id",
    )
    customer: Customer | None = Relationship(back_populates="tickets")

    retrieval_score: float | None = Field(default=None)

    generated_response: str | None = Field(default=None)
    llm_confidence: float | None = Field(default=None)

    semantic_similarity: float | None = Field(default=None)
    final_confidence: float | None = Field(default=None)

    routing_decision: RoutingDecision | None = Field(default=None)
    judge_tone_empathy: float | None = None
    judge_response_quality: float | None = None
    judge_faithfulness: float | None = None
    judge_groundedness: float | None = None
    judge_overall: float | None = None
    judge_pass: bool | None = None
    judge_reason: str | None = None

    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),  # Database-side default
            onupdate=func.now(),
            nullable=False,
        ),
    )
    
    def __repr__(self):
        return self.customer.full_name
