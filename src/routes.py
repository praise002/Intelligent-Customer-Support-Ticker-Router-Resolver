
import logging

from fastapi import APIRouter, Request

from scripts import vector_store
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
async def zendesk_webhook(request: Request):
    """
    This endpoint receives webhook notifications from Zendesk
    """
    # Get the JSON data sent by Zendesk
    payload = await request.json()
    
    logging.info(f"Received webhook: {payload}")
    
    # Extract ticket information
    ticket_id = payload.get("id")
    subject = payload.get("subject")
    _ = payload.get("description")
    
    # Your processing logic here
    print(f"New ticket created: {ticket_id} - {subject}")
    
    return {"status": "received"}