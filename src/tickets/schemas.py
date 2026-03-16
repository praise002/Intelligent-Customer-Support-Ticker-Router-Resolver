from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field

from constants import Priority

class ZendeskWebhookPayload(BaseModel):
    id: str
    subject: str
    description: str
    status: str
    priority: str
    requester_email: str
    created_at: str

# class Ticket(BaseModel):
#     """Incoming support ticket"""

#     ticket_id: str
#     subject: str
#     description: str
#     category: str | None = None
#     priority: str | None = Priority.MEDIUM
#     created_at: datetime = Field(default_factory=datetime.now)


# class RetrievedDoc(BaseModel):
#     """Retrieved document from vector store"""

#     content: str
#     metadata: dict
#     relevance_score: float


# class ConfidenceSignals(BaseModel):
#     """Individual confidence signals"""

#     retrieval_quality: float = Field(ge=0.0, le=1.0)
#     semantic_similarity: float = Field(ge=0.0, le=1.0)
#     llm_confidence: float = Field(ge=0.0, le=1.0)
#     final_confidence: float = Field(ge=0.0, le=1.0)

#     def calculate_final(self) -> float:
#         """Calculate weighted final confidence"""
#         return (
#             0.4 * self.retrieval_quality  # How good are the docs?
#             + 0.4 * self.semantic_similarity  # Does response match docs?
#             + 0.2 * self.llm_confidence  # LLM's self-rating
#         )


# # class Resolution(BaseModel):
# #     """AI-generated resolution"""

# #     response_text: str
# #     confidence_signals: ConfidenceSignals
# #     action: Literal["auto_resolve", "human_review", "escalate"]
# #     reasoning: str
# #     retrieved_docs: List[RetrievedDoc]





