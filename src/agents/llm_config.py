import logging
from typing import Optional, Type

from decouple import config
from pydantic import BaseModel

from src.tickets.schemas import LLMProvider, SupportResponse


def get_llm_client(
    provider: LLMProvider = None, output_model: Optional[Type[BaseModel]] = None
):
    """
    Get LLM client with structured output support.
    Auto-detects provider based on available API keys if not specified.
    """

    if provider is None:
        provider = auto_detect_llm_provider()

    if provider == LLMProvider.NVIDIA:
        return _get_nvidia_llm(output_model)
    elif provider == LLMProvider.GROQ:
        return _get_groq_llm(output_model)
    elif provider == LLMProvider.OPENAI:
        return _get_openai_llm(output_model)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def auto_detect_llm_provider() -> LLMProvider:
    """Auto-detect which LLM provider to use based on available API keys"""

    nvidia_key = config("NVIDIA_API_KEY", default=None)
    groq_key = config("GROQ_API_KEY", default=None)
    openai_key = config("OPENAI_API_KEY", default=None)

    if nvidia_key:
        logging.info("🔍 Auto-detected: NVIDIA API key")
        return LLMProvider.NVIDIA
    elif groq_key:
        logging.info("🔍 Auto-detected: Groq API key")
        return LLMProvider.GROQ
    elif openai_key:
        logging.info("🔍 Auto-detected: OpenAI API key")
        return LLMProvider.OPENAI
    else:
        raise ValueError(
            "No LLM API key found. Set NVIDIA_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY"
        )


def _get_nvidia_llm(output_model: Optional[Type[BaseModel]] = None):
    from langchain_nvidia_ai_endpoints import ChatNVIDIA

    llm = ChatNVIDIA(
        model="meta/llama-3.1-70b-instruct", api_key=config("NVIDIA_API_KEY")
    )
    if output_model:
        llm = llm.with_structured_output(output_model)
    return llm


def _get_groq_llm(output_model: Optional[Type[BaseModel]] = None):
    from langchain_groq import ChatGroq

    llm = ChatGroq(
        api_key=config("GROQ_API_KEY"), model="llama-3.3-70b-versatile", temperature=0.1
    )
    if output_model:
        llm = llm.with_structured_output(output_model)
    return llm


def _get_openai_llm(output_model: Optional[Type[BaseModel]] = None):
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    if output_model:
        llm = llm.with_structured_output(output_model)
    return llm
