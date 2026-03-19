from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm_config import get_llm_client
from agents.workflow_state import TicketState
from agents.zendesk_client import (
    assign_for_review,
    escalate_ticket,
    send_response_to_customer,
)
from src.tickets.schemas import RoutingDecision
from src.utility import ConfidenceCalculator

# Initialize LLM (do this once, cached in Celery worker)

llm = get_llm_client()
# llm = get_llm_client(LLMProvider.GROQ)


# NODE 1: Generate Response
def generate_response_node(state: TicketState) -> TicketState:
    """
    Uses LLM + RAG context to generate a response.
    """

    system_prompt = f"""You are a helpful customer support agent.
    
    Use the following knowledge base context to answer the customer's question.
    If you cannot answer confidently based on the context, say so.
    
    Context from knowledge base:
    {state['rag_context']}
    
    Customer issue type: {state['classification']['issue_type']}
    Urgency: {state['classification']['urgency']}
    
    Confidence scale:
    - 1.0 = Completely certain from documentation
    - 0.8-0.9 = Very confident, answer found in context
    - 0.6-0.7 = Somewhat confident, may need verification
    - 0.4-0.5 = Low confidence, recommend escalation
    - 0.0-0.3 = Cannot answer, must escalate
    """

    user_message = f"""Subject: {state['subject']}
    
    Question: {state['description']}
    
    Please provide a helpful response. Also rate your confidence (0.0-1.0) 
    that this answer fully resolves the customer's issue."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    response = llm.invoke(messages)

    state["generated_response"] = response.response
    state["llm_confidence"] = response.confidence

    return state


# NODE 2: Calculate Final Confidence


def calculate_confidence_node(state: TicketState) -> TicketState:
    """
    Implements the confidence formula:

    confidence = (
        0.4 * retrieval_score +
        0.3 * semantic_similarity +
        0.3 * llm_self_score
    )

    Updates state with:
    - semantic_similarity
    - final_confidence
    """

    # Calculate semantic similarity between query and retrieved docs

    calc = ConfidenceCalculator()
    query = f"{state['subject']}. {state['description']}"

    semantic_similarity = calc.calculate_similarity(query, state["rag_context"])

    # Apply your formula
    final_confidence = (
        0.4 * state["retrieval_score"]
        + 0.3 * semantic_similarity
        + 0.3 * state["llm_confidence"]
    )

    state["semantic_similarity"] = semantic_similarity
    state["final_confidence"] = final_confidence

    return state


# NODE 3: Auto Resolve


def auto_resolve_node(state: TicketState) -> TicketState:
    """
    Sends response to customer automatically via Zendesk API.
    Also stores the ticket+response in knowledge base (feedback loop).

    Updates state with:
    - routing_decision = "auto_resolve"
    """

    # Send to customer via Zendesk

    send_response_to_customer(
        ticket_id=state["ticket_id"], response=state["generated_response"]
    )

    # Store in database
    # TODO:
    # add_resolved_ticket(
    #     ticket_id=state["ticket_id"],
    #     question=f"{state['subject']}. {state['description']}",
    #     answer=state["generated_response"],
    #     metadata={
    #         "issue_type": state["classification"]["issue_type"],
    #         "confidence": state["final_confidence"],
    #     },
    # )

    state["routing_decision"] = RoutingDecision.AUTO_RESOLVE

    return state


# NODE 4: Human Review


def human_review_node(state: TicketState) -> TicketState:
    """
    Assigns ticket to human for review before sending.
    Updates Zendesk with internal note containing draft response.
    """

    assign_for_review(
        ticket_id=state["ticket_id"],
        draft_response=state["generated_response"],
        confidence=state["final_confidence"],
        issue_type=state["classification"]["issue_type"],
        urgency=state["classification"]["urgency"],
    )

    state["routing_decision"] = RoutingDecision.HUMAN_REVIEW

    return state


# NODE 5: Escalate


def escalate_node(state: TicketState) -> TicketState:
    """
    Escalates to specialist team based on issue type.
    """

    escalate_ticket(
        ticket_id=state["ticket_id"],
        issue_type=state["classification"]["issue_type"],
        attempted_response=state["generated_response"],
        confidence=state["final_confidence"],
        urgency=state["classification"]["urgency"],
    )

    state["routing_decision"] = RoutingDecision.ESCALATE

    return state


def route_by_confidence(state: TicketState) -> str:
    """
    Routes to next node based on confidence score.

    Returns:
    - "auto_resolve" if confidence > 0.85
    - "human_review" if 0.6 <= confidence <= 0.85
    - "escalate" if confidence < 0.6
    """

    confidence = state["final_confidence"]

    if confidence > 0.85:
        return "auto_resolve"
    elif confidence >= 0.6:
        return "human_review"
    else:
        return "escalate"
