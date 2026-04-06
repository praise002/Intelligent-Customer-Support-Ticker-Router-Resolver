import os
from enum import Enum

import numpy as np
from decouple import config


class EmbeddingProvider(str, Enum):
    """Supported embedding providers for confidence calculation."""

    VLLM = "vllm"
    NVIDIA = "nvidia"
    SENTENCE_TRANSFORMER = "sentence_transformer"


class ConfidenceCalculator:
    """Calculate semantic similarity for confidence scoring"""

    def __init__(self, provider: EmbeddingProvider = None):
        self.provider = provider or self._auto_detect_provider()
        self.model = self._initialize_model()
        print(f"ConfidenceCalculator initialized with {self.provider.value} provider.")

    def _auto_detect_provider(self) -> EmbeddingProvider:
        """Auto-detect provider based on environment variables."""
        if os.getenv("EMBEDDING_API_URL", default=None):
            print("Auto-detected: Found EMBEDDING_API_URL, using vLLM.")
            return EmbeddingProvider.VLLM
        elif config("NVIDIA_API_KEY", default=None):
            print("Auto-detected: Found NVIDIA_API_KEY, using NVIDIA.")
            return EmbeddingProvider.NVIDIA
        else:
            print("Auto-detected: No specific keys, using local SentenceTransformer.")
            return EmbeddingProvider.SENTENCE_TRANSFORMER

    def _initialize_model(self):
        """Returns the appropriate embedding model based on the provider."""
        if self.provider == EmbeddingProvider.VLLM:
            return self._init_vllm_embeddings()
        elif self.provider == EmbeddingProvider.NVIDIA:
            return self._init_nvidia_embeddings()
        elif self.provider == EmbeddingProvider.SENTENCE_TRANSFORMER:
            return self._init_sentence_transformer_embeddings()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _init_vllm_embeddings(self):
        """Initializes embeddings for a generic OpenAI-compatible endpoint."""
        from langchain_openai import OpenAIEmbeddings

        base_url = os.getenv("EMBEDDING_API_URL", default=None)

        model_name = os.getenv("EMBEDDING_MODEL_NAME", default=None)
        return OpenAIEmbeddings(
            model=model_name,
            base_url=base_url,
            api_key="not-needed",
            check_embedding_ctx_length=False,
        )

    def _init_nvidia_embeddings(self):
        """Initializes NVIDIA embeddings."""
        from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

        return NVIDIAEmbeddings(
            api_key=config("NVIDIA_API_KEY"),
            model="nvidia/nv-embed-v1",
            truncate="NONE",
        )

    def _init_sentence_transformer_embeddings(self):
        """Initializes local SentenceTransformer embeddings."""
        from langchain_community.embeddings import SentenceTransformerEmbeddings

        return SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

    async def calculate_similarity(self, query: str, context: str) -> float:
        """
        Calculates semantic similarity between a query and a context using the
        initialized embedding model.

        Returns a float between 0 and 1.
        """
        # Generate embeddings for the query and the context in parallel
        query_embedding, context_embedding = await self.model.aembed_documents(
            [query, context]
        )

        # Calculate cosine similarity
        similarity = np.dot(query_embedding, context_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(context_embedding)
        )

        # Normalize the score to a 0-1 range for confidence
        return float((similarity + 1) / 2)
