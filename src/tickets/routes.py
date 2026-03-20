import logging

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from scripts import vector_store
from src.db.main import get_session
from src.tickets.schemas import TicketCreate, ZendeskWebhookPayload
from src.tickets.service import create_ticket
from src.tickets.tasks import classify_ticket_task

# from src import initialize_components

# Initialize components (lazy loading)
vector_store = None
llm_generator = None
confidence_calc = None
workflow = None

router = APIRouter()


@router.get("/health")
async def health():
    """Detailed health check"""
    try:
        # initialize_components()
        stats = vector_store.get_collection_stats()

        return {
            "status": "healthy",
            "vector_store": {
                "chunks": stats["total_chunks"],
                "collection": stats["collection_name"],
            },
            "llm_provider": (
                llm_generator.provider if llm_generator else "not initialized"
            ),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.post("/webhook/ticket-created")
async def zendesk_webhook(
    payload: ZendeskWebhookPayload, session: AsyncSession = Depends(get_session)
):
    """
    This endpoint receives and validates webhook notifications from Zendesk
    """
    logging.info(f"Received webhook: {payload}")

    ticket_id = payload.id
    subject = payload.subject
    description = payload.description

    print(f"New ticket created: {ticket_id} - {subject}")
    print(f"Description: {description}")

    ticket_data = TicketCreate(
        ticket_id=payload.id,
        subject=payload.subject,
        content=payload.description,
        email=payload.requester_email,
    )

    task = classify_ticket_task.delay(payload.id, payload.subject, payload.description)
    print(task)
    await create_ticket(session, ticket_data)

    return {"status": "received"}



