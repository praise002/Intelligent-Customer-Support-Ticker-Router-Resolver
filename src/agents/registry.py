import logging
from decouple import config as c

from src.agents.classifier import TicketClassifier
from src.agents.confidence import ConfidenceCalculator
from src.agents.llm_config import get_llm_client
from src.agents.workflow_graph import create_ticket_workflow
from src.scripts.vector_store import VectorStoreManager

logger = logging.getLogger(__name__)

_registry: dict = {}


def get_registry() -> dict:
    global _registry

    if _registry:
        logger.info("AI components already loaded. Skipping re-init.")
        return _registry

    logger.info("Initializing AI components...")
    _registry = {
        "llm_client": get_llm_client(),
        "vector_store": VectorStoreManager(),
        "confidence_calculator": ConfidenceCalculator(),
        "ticket_classifier": TicketClassifier(api_token=c("NVIDIA_API_KEY")),
        "workflow": create_ticket_workflow(),
    }
    logger.info("AI components initialized successfully.")

    return _registry