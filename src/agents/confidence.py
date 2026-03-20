import numpy as np
from sentence_transformers import SentenceTransformer


class ConfidenceCalculator:
    """Calculate semantic similarity for confidence scoring"""

    def __init__(self):
        # Load small, fast embedding model for similarity
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def calculate_similarity(self, query: str, context: str) -> float:
        """
        Calculate semantic similarity between query and context.

        Returns: float between 0-1 (1 = identical meaning)
        """
        query_embedding = self.model.encode(query)
        context_embedding = self.model.encode(context)

        similarity = np.dot(query_embedding, context_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(context_embedding)
        )

        # Normalize to 0-1 range
        return float((similarity + 1) / 2)
