import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from lark import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from src.agents.llm_config import get_llm_client
from src.agents.zendesk_client import create_single_ticket
from src.db.main import get_session
from src.guardrails.input_validator import validate_input
from src.tickets.dependencies import get_vector_store
from src.tickets.schemas import TicketCreate, WebFormTicket, ZendeskWebhookPayload
from src.tickets.service import create_ticket
from src.tickets.tasks import classify_ticket_task

router = APIRouter()


@router.get("/health")
async def health(
    request: Request,
    vector_store=Depends(get_vector_store),
    llm_generator=Depends(get_llm_client),
):
    """Detailed health check"""
    try:

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
    print(payload)
    ticket_id = payload.id
    subject = payload.subject
    description = payload.description

    # validation = validate_input(
    #     subject=payload.subject, description=payload.description
    # )

    # if not validation.safe:
    #     logger.warning(
    #         f"🚫 Blocked ticket {payload.id}: {validation.reason} "
    #         f"(category: {validation.category})"
    #     )

    #     # TODO: Alert if spike in blocked tickets

    #     return {"status": "blocked"}

    ticket_data = TicketCreate(
        ticket_id=payload.id,
        subject=payload.subject,
        content=payload.description,
        email=payload.requester_email,
    )
    print(f"New ticket created: {ticket_id} - {subject}")
    print(f"Description: {description}")

    task = classify_ticket_task.delay(payload.id, payload.subject, payload.description)
    print(task)
    await create_ticket(session, ticket_data)

    return {"status": "received"}


@router.post("/submit-ticket")
async def submit_web_form_ticket(ticket: WebFormTicket):
    """
    Direct ticket submission from web form.
    """
    payload = {
        "subject": ticket.subject,
        "comment": {"body": ticket.content},
        "requester": {"email": ticket.email, "name": ticket.name},
        "priority": "normal",
        "status": "new",
    }
    
    try:
        zendesk_ticket = await create_single_ticket(payload)
        print(zendesk_ticket)
        
        logger.info(f"✅ Ticket created in Zendesk: #{zendesk_ticket['id']}")
        
        return {
            "status": "success",
            "message": "Ticket submitted successfully!",
            "ticket_id": zendesk_ticket["id"]
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to create Zendesk ticket: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit ticket: {str(e)}"
        )
