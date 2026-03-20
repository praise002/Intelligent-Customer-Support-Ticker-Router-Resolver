from typing import Dict, List, Optional, TypedDict

from src.tickets.schemas import RoutingDecision


class TicketState(TypedDict):
    """
    State that gets passed between LangGraph nodes.

    This tracks everything about the ticket as it moves
    through the workflow.
    """

    # Input data
    ticket_id: int
    subject: str
    description: str
    classification: Dict  # {issue_type, urgency, issue_score, urgency_score}

    # RAG results
    rag_documents: List[Dict]  # Retrieved docs from ChromaDB
    rag_context: str  # Concatenated doc content
    retrieval_score: float  # Average similarity

    # LLM generation
    generated_response: Optional[str]
    llm_confidence: Optional[float]

    # Confidence calculation
    semantic_similarity: Optional[float]
    final_confidence: Optional[float]

    # Routing
    routing_decision: Optional[RoutingDecision]

    # Metadata
    error: Optional[str]
    retry_count: int
