from langgraph.graph import END, StateGraph

from agents.workflow_nodes import (
    auto_resolve_node,
    calculate_confidence_node,
    escalate_node,
    generate_response_node,
    human_review_node,
    route_by_confidence,
)
from agents.workflow_state import TicketState


def create_ticket_workflow() -> StateGraph:
    """
    Creates the LangGraph workflow for ticket processing.

    This is the multi-step decision tree.
    """

    workflow = StateGraph(TicketState)

    workflow.add_node("generate_response", generate_response_node)
    workflow.add_node("calculate_confidence", calculate_confidence_node)
    workflow.add_node("auto_resolve", auto_resolve_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("escalate", escalate_node)

    # ADD EDGES (Flow between nodes)

    # Start → Generate Response
    workflow.set_entry_point("generate_response")

    # Generate Response → Calculate Confidence (always)
    workflow.add_edge("generate_response", "calculate_confidence")

    # Calculate Confidence → Route based on score (conditional)
    workflow.add_conditional_edges(
        "calculate_confidence",
        route_by_confidence,  # Function decides next node
        {
            "auto_resolve": "auto_resolve",
            "human_review": "human_review",
            "escalate": "escalate",
        },
    )

    # All terminal nodes end the workflow
    workflow.add_edge("auto_resolve", END)
    workflow.add_edge("human_review", END)
    workflow.add_edge("escalate", END)

    app = workflow.compile()

    return app
