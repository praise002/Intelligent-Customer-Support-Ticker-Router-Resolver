import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from lark import logger
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from src.agents.llm_config import get_llm_client
from src.agents.zendesk_client import create_single_ticket
from src.db.main import get_session
from src.guardrails.input_validator import validate_input
from src.tickets.dependencies import get_vector_store
from src.tickets.schemas import (
    SUCCESS_EXAMPLE,
    TicketCreate,
    TicketResponse,
    TicketResponseData,
    WebFormTicket,
    ZendeskWebhookPayload,
)
from src.tickets.service import block_ticket, create_ticket, get_all_tickets
from src.tickets.tasks import classify_ticket_task

router = APIRouter()


@router.get("/healthcheck", include_in_schema=False)
async def health():
    return {"status": "ok"}


@router.get("/health")
async def health(
    _: Request,
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
            "llm_provider": (llm_generator),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.post("/webhook/ticket-created", include_in_schema=False)
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

    validation = validate_input(
        subject=payload.subject, description=payload.description
    )

    if not validation.safe:
        logger.warning(
            f"Blocked ticket {payload.id}: {validation.reason}"
            f"(category: {validation.category})"
        )

        await block_ticket(
            session=session,
            ticket_id=payload.id,
            reason=validation.reason,
            category=validation.category,
        )

        return {"status": "blocked"}

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
async def submit_web_form_ticket(
    ticket: WebFormTicket, session: AsyncSession = Depends(get_session)
):
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

    validation = validate_input(subject=ticket.subject, description=ticket.content)

    if not validation.safe:
        logger.warning(
            f"Blocked ticket {ticket.ticket_id}: {validation.reason}"
            f"(category: {validation.category})"
        )

        await block_ticket(
            session=session,
            reason=validation.reason,
            category=validation.category,
        )

        return {"status": "blocked"}

    try:
        zendesk_ticket = await create_single_ticket(payload)
        print(f"Zendesk ticket created: {zendesk_ticket}")

        # Extract ticket ID and ensure it's serializable
        ticket_id = zendesk_ticket.get("id")
        if not ticket_id:
            raise ValueError(f"No ticket ID in Zendesk response: {zendesk_ticket}")

        logger.info(f"Ticket created in Zendesk: #{ticket_id}")

        # Prepare local DB data
        ticket_data = TicketCreate(
            ticket_id=str(ticket_id),
            subject=ticket.subject,
            content=ticket.content,
            email=ticket.email,
            name=ticket.name,
        )

        try:
            await create_ticket(session, ticket_data)
            logger.info(f"Ticket saved to local DB: {ticket_id}")
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            raise HTTPException(
                status_code=500, detail=f"Database error: {str(db_error)}"
            )

        try:
            # Ensure all arguments are JSON-serializable (strings, not objects)
            task = classify_ticket_task.delay(
                int(ticket_id),  
                str(ticket.subject),
                str(ticket.content),
            )
            logger.info(f"Celery task dispatched: {task.id}")
        except Exception as celery_error:
            # Log but don't fail the request - ticket is already created
            logger.error(f"Celery task failed to dispatch: {celery_error}")
            # Optionally retry or alert, but return success to user

        return {
            "status": "success",
            "message": "Ticket submitted successfully!",
            "ticket_id": ticket_id,
        }

    except HTTPException:
        raise  # Re-raise FastAPI exceptions as-is
    except Exception as e:
        logger.exception(f"💥 Unexpected error in submit-ticket: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/tickets", response_model=TicketResponse)
async def get_tickets(
    limit: int = Query(20, ge=1, le=100, description="Number of tickets"),
    offset: int = Query(0, ge=0, description="Skip tickets"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get list of all tickets with pagination

    EXAMPLE:
    - GET /tickets/ → First 20 tickets
    - GET /tickets/?limit=10&offset=20 → Tickets 21-30
    """
    tickets = await get_all_tickets(session=session, limit=limit, offset=offset)
    return TicketResponse(
        status=SUCCESS_EXAMPLE,
        message="Tickets retrieved successfully",
        data=[TicketResponseData.model_validate(t) for t in tickets],
    )


@router.delete("/tickets/delete-all", status_code=204)
async def delete_all_tickets(session: AsyncSession = Depends(get_session)):
    try:
        await session.exec(text("TRUNCATE TABLE ticket CASCADE;"))
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(500, detail=str(e))
