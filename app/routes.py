import json
from pathlib import Path
from typing import List

from fastapi import HTTPException

import app
from app import initialize_components
from app.schemas import TicketInput, TicketResponse
from scripts import vector_store

# Initialize components (lazy loading)
vector_store = None
llm_generator = None
confidence_calc = None
workflow = None


@app.get("/health")
async def health():
    """Detailed health check"""
    try:
        initialize_components()
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


@app.post("/tickets", response_model=TicketResponse)
async def process_ticket(ticket: TicketInput):
    """Process a single support ticket"""
    try:
        initialize_components()

        # Create ticket dict
        ticket_dict = {
            "ticket_id": f"TKT-{hash(ticket.subject) % 10000:04d}",
            "subject": ticket.subject,
            "description": ticket.description,
            "priority": ticket.priority,
            "category": ticket.category,
        }

        # Process through workflow
        result = workflow.process_ticket(ticket_dict)

        return TicketResponse(
            ticket_id=ticket_dict["ticket_id"],
            action=result["action"],
            confidence=result["confidence_signals"].get("final_confidence", 0.0),
            response=result["llm_response"],
            reasoning=result["reasoning"],
            processing_time=result["processing_time"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    """Get ticket status (mock endpoint for demo)"""
    return {
        "ticket_id": ticket_id,
        "status": "processed",
        "message": "This is a demo endpoint",
    }


@app.post("/tickets/batch")
async def process_batch(tickets: List[TicketInput]):
    """Process multiple tickets in batch"""
    try:
        initialize_components()

        # Convert to ticket dicts
        ticket_dicts = []
        for i, ticket in enumerate(tickets):
            ticket_dicts.append(
                {
                    "ticket_id": f"BATCH-{i+1:03d}",
                    "subject": ticket.subject,
                    "description": ticket.description,
                    "priority": ticket.priority,
                    "category": ticket.category,
                }
            )

        # Process batch
        batch_result = workflow.process_batch(ticket_dicts)

        return {
            "summary": batch_result["summary"],
            "results": [
                {
                    "ticket_id": r["ticket"]["ticket_id"],
                    "action": r["action"],
                    "confidence": r["confidence_signals"].get("final_confidence", 0.0),
                }
                for r in batch_result["results"]
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/demo/tickets")
async def get_demo_tickets():
    """Get pre-configured demo tickets"""
    try:
        demo_file = Path("data/demo_tickets.json")
        if demo_file.exists():
            with open(demo_file, "r") as f:
                tickets = json.load(f)
            return {"tickets": tickets}
        else:
            return {"tickets": [], "message": "Demo tickets not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/demo/run")
async def run_demo():
    """Run the full demo with curated tickets"""
    try:
        initialize_components()

        # Load demo tickets
        demo_file = Path("data/demo_tickets.json")
        with open(demo_file, "r") as f:
            demo_tickets = json.load(f)

        # Process each demo ticket
        results = []
        for ticket in demo_tickets[:3]:  # Just the 3 main demo tickets
            result = workflow.process_ticket(ticket)
            results.append(
                {
                    "ticket": ticket,
                    "action": result["action"],
                    "confidence": result["confidence_signals"].get(
                        "final_confidence", 0.0
                    ),
                    "response": result["llm_response"],
                    "reasoning": result["reasoning"],
                    "signals": result["confidence_signals"],
                }
            )

        return {"demo_results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    try:
        initialize_components()
        stats = vector_store.get_collection_stats()

        return {
            "vector_store": stats,
            "thresholds": {"high_confidence": 0.85, "medium_confidence": 0.60},
            "weights": {
                "retrieval_quality": 0.4,
                "semantic_similarity": 0.4,
                "llm_confidence": 0.2,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
