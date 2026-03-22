from decouple import config

from src.tickets.schemas import LLMProvider, SupportResponse


def get_llm_client(provider: LLMProvider = None):
    """
    Get LLM client with structured output support.
    Auto-detects provider based on available API keys if not specified.
    """

    if provider is None:
        provider = auto_detect_llm_provider()

    if provider == LLMProvider.NVIDIA:
        return _get_nvidia_llm()
    elif provider == LLMProvider.GROQ:
        return _get_groq_llm()
    elif provider == LLMProvider.OPENAI:
        return _get_openai_llm()
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def auto_detect_llm_provider() -> LLMProvider:
    """Auto-detect which LLM provider to use based on available API keys"""

    nvidia_key = config("NVIDIA_API_KEY", default=None)
    groq_key = config("GROQ_API_KEY", default=None)
    openai_key = config("OPENAI_API_KEY", default=None)

    if nvidia_key:
        print("🔍 Auto-detected: NVIDIA API key")
        return LLMProvider.NVIDIA
    elif groq_key:
        print("🔍 Auto-detected: Groq API key")
        return LLMProvider.GROQ
    elif openai_key:
        print("🔍 Auto-detected: OpenAI API key")
        return LLMProvider.OPENAI
    else:
        raise ValueError(
            "No LLM API key found. Set NVIDIA_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY"
        )


def _get_nvidia_llm():
    """Initialize NVIDIA LLM with structured output"""
    from langchain_nvidia_ai_endpoints import ChatNVIDIA

    return ChatNVIDIA(
        model="meta/llama-3.1-70b-instruct", api_key=config("NVIDIA_API_KEY")
    ).with_structured_output(SupportResponse)


def _get_groq_llm():
    """Initialize Groq LLM with structured output"""
    from langchain_groq import ChatGroq

    return ChatGroq(
        api_key=config("GROQ_API_KEY"), model="llama-3.3-70b-versatile", temperature=0.1
    ).with_structured_output(SupportResponse) 


def _get_openai_llm():
    """Initialize OpenAI LLM with structured output"""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model="gpt-4o-mini", temperature=0.1).with_structured_output(
        SupportResponse
    )
