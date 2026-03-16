import logging

from celery import Task
from celery_config import celery_app

from agents.classifier import TicketClassifier
from src.utility import get_priority_score

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


@celery_app.task(
    name="tasks.process_llm",
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    time_limit=300,
)
def process_llm_task(
    self: Task, ticket_id: str, subject: str, description: str, classification: dict
):
    """
    Process ticket through LLM (pulled from priority queue)
    """
    try:
        urgency = classification["urgency"]
        issue_type = classification["issue_type"]

        logger.info(
            f"🤖 Processing {urgency} priority {issue_type} ticket {ticket_id}..."
        )

        # For now, just simulate LLM processing
        # Later you'll add: RAG search, LLM generation, confidence calculation

        import time

        time.sleep(2)  # Simulate LLM processing (5 seconds in real system)

        logger.info(f"✅ Ticket {ticket_id} processed successfully")

        return {
            "ticket_id": ticket_id,
            "classification": classification,
            "status": "processed",
        }

    except Exception as e:
        logger.error(f"❌ LLM processing failed for ticket {ticket_id}: {e}")
        raise
