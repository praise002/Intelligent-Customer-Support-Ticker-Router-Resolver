import logging

from celery import Task

from agents.classifier import TicketClassifier
from scripts.vector_store import VectorStoreManager
from src.db.main import get_session
from src.tickets.schemas import TicketUpdate
from src.tickets.service import get_ticket_by_id, update_ticket
from src.utility import get_priority_score

from .celery_config import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.classify_ticket",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
)
def classify_ticket_task(self: Task, ticket_id: int, subject: str, description: str):
    """
    Classify the ticket (runs in background worker)

    Returns classification and adds to priority queue for next step
    """
    try:
        # Load classifier once per worker (cached)
        if not hasattr(self, "classifier"):
            logger.info("Loading classifier in worker...")
            self.classifier = TicketClassifier()

        ticket_text = f"{subject}. {description}"
        classification = self.classifier.classify(ticket_text)

        issue_type = classification["issue_type"]
        urgency = classification["urgency"]

        priority = get_priority_score(urgency)

        logger.info(
            f"📬 Adding ticket {ticket_id} to priority queue "
            f"(urgency={urgency}, priority={priority}, issue_type={issue_type})"
        )

        process_llm_task.apply_async(
            args=[ticket_id, subject, description, classification],
            queue="processing",
            priority=priority,
        )

        return {
            "ticket_id": ticket_id,
            "classification": classification,
            "priority": priority,
            "queued_for": "llm_processing",
        }

    except Exception as e:
        logger.error(f"❌ Classification failed for {ticket_id}: {e}")
        raise


@celery_app.task(bind=True)
async def process_llm_task(
    self: Task, ticket_id: str, subject: str, description: str, classification: dict
):
    """
    Process ticket through LangGraph workflow.
    """
    from agents.workflow_graph import create_ticket_workflow

    # Initialize workflow (cached in worker)
    if not hasattr(self, "workflow"):
        self.workflow = create_ticket_workflow()

    # Initialize vector store (cached in worker)
    if not hasattr(self, "vector_store"):
        self.vector_store = VectorStoreManager()

    query = f"{subject}. {description}"
    rag_docs = self.vector_store.search(query, top_k=5)

    initial_state = {
        "ticket_id": ticket_id,
        "subject": subject,
        "description": description,
        "classification": classification,
        "rag_documents": rag_docs,
        "rag_context": "\n\n".join([d["content"] for d in rag_docs]),
        "retrieval_score": sum(d["relevance_score"] for d in rag_docs) / len(rag_docs),
        "retry_count": 0,
    }

    final_state = self.workflow.invoke(initial_state)

    logger.info(
        f"✅ Ticket {ticket_id} processed: "
        f"{final_state['routing_decision']} "
        f"(confidence: {final_state['final_confidence']:.2%})"
    )

    update_data = TicketUpdate(
        retrieval_score=final_state.get("retrieval_score"),
        generated_response=final_state.get("generated_response"),
        llm_confidence=final_state.get("llm_confidence"),
        semantic_similarity=final_state.get("semantic_similarity"),
        final_confidence=final_state.get("final_confidence"),
        routing_decision=final_state.get("routing_decision"),
    )

    async for session in get_session():
        db_ticket = await get_ticket_by_id(session, ticket_id)
        if db_ticket:
            await update_ticket(
                session=session, db_ticket=db_ticket, ticket_in=update_data
            )
            logger.info(f"Successfully updated ticket {ticket_id} in the database.")
        else:
            logger.error(f"Could not find ticket {ticket_id} in DB to update.")

    return final_state
