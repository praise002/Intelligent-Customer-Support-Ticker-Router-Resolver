import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from lark import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from src.agents.llm_config import get_llm_client
from src.agents.zendesk_client import create_single_ticket
from src.db.main import get_session

# from src.guardrails.input_validator import validate_input
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


# @router.post("/submit-ticket")
# async def submit_web_form_ticket(
#     ticket: WebFormTicket, session: AsyncSession = Depends(get_session)
# ):
#     """
#     Direct ticket submission from web form.
#     """
#     payload = {
#         "subject": ticket.subject,
#         "comment": {"body": ticket.content},
#         "requester": {"email": ticket.email, "name": ticket.name},
#         "priority": "normal",
#         "status": "new",
#     }

#     try:
#         zendesk_ticket = await create_single_ticket(payload)
#         print(zendesk_ticket)

#         logger.info(f"Ticket created in Zendesk: #{zendesk_ticket['id']}")
#         ticket_id = zendesk_ticket["id"]
#         ticket_data = TicketCreate(
#             ticket_id=ticket_id,
#             subject=ticket.subject,
#             content=ticket.content,
#             email=ticket.email,
#             name=ticket.name,
#         )
        
#         task = classify_ticket_task.delay(ticket_id , ticket.subject, ticket.content)
#         print(task)
#         await create_ticket(session, ticket_data)

#         return {
#             "status": "success",
#             "message": "Ticket submitted successfully!",
#             "ticket_id": zendesk_ticket["id"],
#         }

#     except RequestValidationError as e:
#         logger.error(f"Validation error: {e.errors()}")
#         raise HTTPException(
#             status_code=422,
#             detail={"message": "Validation error", "errors": e.errors()},
#         )
#     except Exception as e:
#         logger.error(f"Failed to create Zendesk ticket: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Failed to submit ticket: {str(e)}"
#         )

# TODO: UNDERSTAND IT LATER
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

    try:
        zendesk_ticket = await create_single_ticket(payload)
        print(f"✅ Zendesk ticket created: {zendesk_ticket}")
        
        # Extract ticket ID and ensure it's serializable
        ticket_id = zendesk_ticket.get("id")
        if not ticket_id:
            raise ValueError(f"No ticket ID in Zendesk response: {zendesk_ticket}")
        
        logger.info(f"Ticket created in Zendesk: #{ticket_id}")
        
        # Prepare local DB data
        ticket_data = TicketCreate(
            ticket_id=str(ticket_id),  # Ensure string if your model expects it
            subject=ticket.subject,
            content=ticket.content,
            email=ticket.email,
            name=ticket.name,
        )
        
        # Create in local DB FIRST, then dispatch Celery task
        try:
            await create_ticket(session, ticket_data)
            logger.info(f"✅ Ticket saved to local DB: {ticket_id}")
        except Exception as db_error:
            logger.error(f"❌ Database error: {db_error}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        
        # Dispatch Celery task AFTER DB commit with error handling
        try:
            # Ensure all arguments are JSON-serializable (strings, not objects)
            task = classify_ticket_task.delay(
                int(ticket_id),  # Explicitly convert to string
                str(ticket.subject),
                str(ticket.content)
            )
            logger.info(f"✅ Celery task dispatched: {task.id}")
        except Exception as celery_error:
            # Log but don't fail the request - ticket is already created
            logger.error(f"⚠️ Celery task failed to dispatch: {celery_error}")
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
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )