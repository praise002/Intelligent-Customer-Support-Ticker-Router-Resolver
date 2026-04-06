import asyncio
import logging

from celery import Task

from src.agents.classifier import TicketClassifier
from src.constant import ISSUE_TYPE_TO_DOC_TYPES
from src.db.main import get_session
from src.db.models import Ticket
from src.scripts.vector_store import VectorStoreManager
from src.tickets.celery_config import celery_app
from src.tickets.schemas import TicketUpdate
from src.tickets.service import (
    count_recently_blocked_tickets,
    get_ticket_by_id,
    update_ticket,
)
from src.utility import get_priority_score, send_slack_alert

logger = logging.getLogger(__name__)


class BaseTicketTask(Task):
    """
    Base class for all ticket tasks.
    on_failure runs automatically after all retries exhausted.
    """

    abstract = True  # tells Celery this is a base, not a real task

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        ticket_id = args[0]  # ticket_id is always first argument
        logger.error(
            f"❌ Task {self.name} permanently failed for ticket {ticket_id}: {exc}"
        )
        asyncio.run(_update_ticket_status(ticket_id, "failed"))


async def _update_ticket_status(ticket_id: int, status: str):
    """Shared async helper to update ticket status"""
    from src.db.main import get_session
    from src.tickets.service import get_ticket_by_id, update_ticket_status

    async for session in get_session():
        ticket = await get_ticket_by_id(session, ticket_id)
        if ticket:
            await update_ticket_status(session, ticket, status)
            logger.info(f"Updated ticket {ticket_id} status → {status}")
        else:
            logger.error(f"Could not find ticket {ticket_id} to mark as {status}")


@celery_app.task(
    name="tasks.classify_ticket",
    bind=True,
    base=BaseTicketTask,
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
            from decouple import config

            logger.info("Loading classifier in worker...")
            hf_token = config("HF_TOKEN", default=None)
            self.classifier = TicketClassifier(api_token=hf_token)

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
    base=BaseTicketTask,
    max_retries=3,
    autoretry_for=(Exception,),
)
def process_llm_task(
    self: Task, ticket_id: str, subject: str, description: str, classification: dict
):
    """
    Process ticket through LangGraph workflow.
    """
    try:
        return asyncio.run(
            _process_llm_async(self, ticket_id, subject, description, classification)
        )
    except Exception as e:
        logger.error(f"❌ LLM processing failed for ticket {ticket_id}: {e}")
        raise


async def _process_llm_async(
    self: Task, ticket_id: str, subject: str, description: str, classification: dict
):

    if not hasattr(self, "workflow"):
        from src.agents.workflow_graph import create_ticket_workflow

        logger.info("Loading workflow in worker...")
        self.workflow = create_ticket_workflow()

    if not hasattr(self, "vector_store"):
        logger.info("Loading vector store in worker...")
        self.vector_store = VectorStoreManager()

    query = f"{subject}. {description}"

    issue_type = classification.get("issue_type")
    doc_types_list = ISSUE_TYPE_TO_DOC_TYPES.get(issue_type, None)

    if doc_types_list:
        # search across multiple doc_types, merge, dedupe, re-rank
        rag_docs = self.vector_store.search_across_doc_types(
            query=query,
            doc_types=doc_types_list,
            top_k=5,
            per_type_k=3,  # retrieve 3 per category → up to 15 candidates before re-rank
            rerank=True,
        )
    else:
        # no specific doc_type filter (e.g., IssueType.general or unknown)
        # Use the standard search with re-ranking enabled
        rag_docs = self.vector_store.search(query, top_k=5, rerank=True)

    retrieval_score = (
        sum(d["relevance_score"] for d in rag_docs) / len(rag_docs) if rag_docs else 0.0
    )

    initial_state = {
        "ticket_id": ticket_id,
        "subject": subject,
        "description": description,
        "classification": classification,
        "rag_documents": rag_docs,
        "rag_context": "\n\n".join([d["content"] for d in rag_docs]),
        "retrieval_score": retrieval_score,
        "retry_count": 0,
    }

    # ainvoke because nodes are async
    final_state = await self.workflow.ainvoke(initial_state)

    logger.info(
        f"✅ Ticket {ticket_id} processed: "
        f"{final_state['routing_decision']} "
        f"(confidence: {final_state['final_confidence']:.2%})"
    )

    update_data = TicketUpdate(
        urgency=classification["urgency"],
        issue_type=classification["issue_type"],
        status="completed",
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
                session=session, ticket=db_ticket, ticket_in=update_data
            )
            logger.info(f"Successfully updated ticket {ticket_id} in database.")
        else:
            logger.error(f"Could not find ticket {ticket_id} in DB to update.")

    return final_state


@celery_app.task(name="tasks.recover_pending_tickets")
def recover_pending_tickets():
    """
    Safety net — finds tickets stuck in pending
    and requeues them.
    """
    tickets = asyncio.run(_get_stuck_pending_tickets())

    if not tickets:
        return

    logger.info(f"🔄 Recovering {len(tickets)} stuck pending tickets...")

    for ticket in tickets:
        classify_ticket_task.apply_async(
            args=[ticket.id, ticket.subject, ticket.description],
            queue="classification",
        )

    logger.info(f"✅ Requeued {len(tickets)} tickets.")


async def _get_stuck_pending_tickets():
    """Find tickets pending"""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from src.db.main import get_session

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)

    async for session in get_session():
        result = await session.exec(
            select(Ticket).where(Ticket.status == "pending", Ticket.created_at < cutoff)
        )
        return result.all()


BLOCKED_TICKET_THRESHOLD = 10  # e.g., 10 tickets
TIME_WINDOW_MINUTES = 60  # e.g., in the last 60 minutes


@celery_app.task(name="tasks.monitor_blocked_tickets")
def monitor_blocked_tickets():
    """
    Periodically checks for a spike in blocked tickets and sends a Slack alert.
    """
    logger.info("Running blocked ticket monitoring task...")
    asyncio.run(_check_blocked_tickets())


async def _check_blocked_tickets():
    """Async helper to count blocked tickets and alert if threshold exceeded."""
    async for session in get_session():
        blocked_count = await count_recently_blocked_tickets(
            session, TIME_WINDOW_MINUTES
        )

        if blocked_count > BLOCKED_TICKET_THRESHOLD:
            message = (
                f"🚨 *Alert: High volume of blocked tickets!*\n"
                f"> {blocked_count} tickets blocked in the last {TIME_WINDOW_MINUTES} minutes."
            )
            logger.warning(message)
            send_slack_alert(message)

        return  # exit after first session
