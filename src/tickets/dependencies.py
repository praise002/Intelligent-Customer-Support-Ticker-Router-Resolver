from typing import Union

from fastapi import Request
from langchain_groq import ChatGroq
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph

from src.agents.classifier import TicketClassifier
from src.agents.confidence import ConfidenceCalculator
from src.scripts.vector_store import VectorStoreManager


def get_llm_client(request: Request) -> Union[ChatNVIDIA, ChatGroq, ChatOpenAI]:
    """Returns the shared LLM client instance."""
    return request.app.state.llm_client


def get_vector_store(request: Request) -> VectorStoreManager:
    """Returns the shared Vector Store instance."""
    return request.app.state.vector_store


def get_confidence_calculator(request: Request) -> ConfidenceCalculator:
    """Returns the shared Confidence Calculator instance."""
    return request.app.state.confidence_calculator


def get_ticket_classifier(request: Request) -> TicketClassifier:
    """Returns the shared Ticket Classifier instance."""
    return request.app.state.ticket_classifier


def get_workflow(request: Request) -> StateGraph:
    """Returns the shared ticket processing workflow instance."""
    return request.app.state.workflow
