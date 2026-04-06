import json
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from decouple import config
from langchain_chroma import Chroma
from langchain_classic.schema import Document
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = config("LANGSMITH_API_KEY")


class EmbeddingProvider(str, Enum):
    """Supported embedding providers"""

    NVIDIA = "nvidia"
    SENTENCE_TRANSFORMER = "sentence_transformer"
    OPENAI = "openai"
    DOCKER_MODEL_RUNNER = "docker_model_runner"


class VectorStoreManager:
    EMBEDDING_CONFIGS = {
        EmbeddingProvider.NVIDIA: {
            "model_name": "nvidia/nv-embed-v1",
            "dimensions": 4096,
            "max_tokens": 2048,
            "chunk_size": 1000,
            "chunk_overlap": 200,
        },
        EmbeddingProvider.SENTENCE_TRANSFORMER: {
            "model_name": "all-MiniLM-L6-v2",
            "dimensions": 384,
            "max_tokens": 256,  # in tokens
            "chunk_size": 950,  # in characters
            "chunk_overlap": 100,  # in characters
        },
        EmbeddingProvider.OPENAI: {
            "model_name": "text-embedding-3-small",
            "dimensions": 1536,
            "max_tokens": 8191,
            "chunk_size": 1000,
            "chunk_overlap": 200,
        },
        EmbeddingProvider.DOCKER_MODEL_RUNNER: {
            "model_name": "ai/all-minilm",
            "dimensions": 384,
            "max_tokens": 256,
            "chunk_size": 950,
            "chunk_overlap": 100,
        },
    }

    def __init__(
        self,
        collection_name: str = "raenest_docs",
        persist_directory: str = "data/chroma_db",
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name

        self.embedding_provider = embedding_provider or self._auto_detect_provider()

        self.config = self.EMBEDDING_CONFIGS[self.embedding_provider]

        self.embeddings = self._initialize_embeddings()

        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(self.persist_directory),
        )
        self._reranker = None
        print(f"📦 Vector store initialized with {self.embedding_provider} embeddings")

    def _get_reranker(self):
        if self._reranker is None:
            from sentence_transformers import CrossEncoder

            self._reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        return self._reranker

    def _auto_detect_provider(self) -> EmbeddingProvider:
        """
        Auto-detect which embedding provider to use based on available API keys.


        """
        nvidia_key = config("NVIDIA_API_KEY", default=None)
        openai_key = config("OPENAI_API_KEY", default=None)
        embedding_url = os.getenv("EMBEDDING_API_URL", default=None)

        if embedding_url:
            logging.info(f"Auto-detected: Docker Model Runner at {embedding_url}")
            return EmbeddingProvider.DOCKER_MODEL_RUNNER
        elif nvidia_key:
            print("🔍 Auto-detected: NVIDIA API key found")
            return EmbeddingProvider.NVIDIA
        elif openai_key:
            print("🔍 Auto-detected: OpenAI API key found")
            return EmbeddingProvider.OPENAI
        else:
            print("🔍 Auto-detected: No API keys, using local SentenceTransformer")
            return EmbeddingProvider.SENTENCE_TRANSFORMER

    def _initialize_embeddings(self):
        """Initialize the embedding model based on provider"""

        if self.embedding_provider == EmbeddingProvider.NVIDIA:
            return self._init_nvidia_embeddings()

        elif self.embedding_provider == EmbeddingProvider.SENTENCE_TRANSFORMER:
            return self._init_sentence_transformer_embeddings()

        elif self.embedding_provider == EmbeddingProvider.OPENAI:
            return self._init_openai_embeddings()

        else:
            raise ValueError(
                f"Unsupported embedding provider: {self.embedding_provider}"
            )

    def _init_docker_model_runner_embeddings(self):
        """
        Initialize embeddings via Docker Model Runner.
        Docker injects EMBEDDING_MODEL_URL automatically when using short syntax.
        The endpoint is OpenAI-compatible so langchain_openai works directly.
        """
        from langchain_openai import OpenAIEmbeddings

        base_url = os.getenv("EMBEDDING_API_URL", default=None)

        model_name = os.getenv("EMBEDDING_MODEL_NAME", default=None)

        if not base_url:
            raise ValueError(
                "Docker Model Runner URL not found. "
                "Ensure EMBEDDING_MODEL_URL is set (injected by Docker Compose models)."
            )

        logging.info(f"Connecting to Docker Model Runner at {base_url}")

        return OpenAIEmbeddings(
            model=model_name,
            base_url=f"{base_url}/v1",  # Docker Model Runner is OpenAI compatible
            api_key="not-needed",  # DMR doesn't require a real key
            check_embedding_ctx_length=False,  # skip OpenAI length validation
        )

    def _init_nvidia_embeddings(self):
        """Initialize NVIDIA embeddings"""
        from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

        nvidia_key = config("NVIDIA_API_KEY", default=None)

        if not nvidia_key:
            raise ValueError("NVIDIA_API_KEY not found in environment")

        os.environ["NVIDIA_API_KEY"] = nvidia_key

        return NVIDIAEmbeddings(
            model=self.config["model_name"],
            truncate="NONE",
        )

    def _init_sentence_transformer_embeddings(self):
        """Initialize SentenceTransformer embeddings (local)"""
        from langchain_community.embeddings import SentenceTransformerEmbeddings

        return SentenceTransformerEmbeddings(model_name=self.config["model_name"])

    def _init_openai_embeddings(self):
        """Initialize OpenAI embeddings"""
        from langchain_openai import OpenAIEmbeddings

        openai_key = config("OPENAI_API_KEY", default=None)

        if not openai_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        os.environ["OPENAI_API_KEY"] = openai_key

        return OpenAIEmbeddings(model=self.config["model_name"])

    def _load_documents_from_json(self, docs_file: str) -> List[Document]:
        """Load documents from JSON and convert to LangChain Documents"""

        with open(docs_file, "r", encoding="utf-8") as f:
            docs_data = json.load(f)

        print(f"Loading {len(docs_data)} documents from {docs_file}")

        # Convert to LangChain Document objects
        documents = []
        for doc in docs_data:
            lc_doc = Document(
                page_content=doc["content"],
                metadata={
                    "source": doc.get("url", "unknown"),
                    "title": doc.get("title", "Untitled"),
                    "doc_type": doc.get("doc_type", "general"),
                },
            )
            documents.append(lc_doc)

        return documents

    def _split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks using RecursiveCharacterTextSplitter"""

        chunk_size = self.config["chunk_size"]
        chunk_overlap = self.config["chunk_overlap"]

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        print("Splitting documents into chunks...")
        splits = text_splitter.split_documents(documents)
        print(f"Created {len(splits)} chunks from {len(documents)} documents")

        return splits

    def load_and_index_documents(
        self,
        docs_file: str = "data/raenest_docs.json",
        batch_size: int = 100,
    ):
        """Load documents from JSON and index them in vector store"""

        # Load documents
        documents = self._load_documents_from_json(docs_file)

        # Split into chunks
        all_splits = self._split_documents(documents)

        # Add to vector store (LangChain handles embedding automatically!)
        print("Adding documents to vector store...")

        # Add in batches to avoid overwhelming API
        all_ids = []
        for i in range(0, len(all_splits), batch_size):
            batch = all_splits[i : i + batch_size]
            ids = self.vector_store.add_documents(documents=batch)
            all_ids.extend(ids)
            print(
                f"   Indexed batch {i//batch_size + 1}/{(len(all_splits)-1)//batch_size + 1}"
            )

        print(f"✅ Indexed {len(all_ids)} chunks successfully!")
        return len(all_ids)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None,
        rerank: bool = True,
        initial_k: int = 20,  # number of candidates to retrieve BEFORE reranking
    ) -> List[Dict]:

        # 1. Retrieve initial_k candidates
        if filter_metadata:
            results = self.vector_store.similarity_search_with_score(
                query=query, k=initial_k, filter=filter_metadata
            )
        else:
            results = self.vector_store.similarity_search_with_score(
                query=query, k=initial_k
            )

        # results is list of (Document, distance) tuples
        candidate_docs = []
        candidate_distances = []
        for doc, dist in results:
            candidate_docs.append(doc)
            candidate_distances.append(dist)

        # 2. Re-rank (if enabled)
        if rerank and candidate_docs:
            from sentence_transformers import CrossEncoder

            reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            scores = reranker.predict(
                [(query, doc.page_content) for doc in candidate_docs]
            )

            # Sort by cross-encoder score (higher is better)
            # Keep both score, doc, and original distance
            scored = list(zip(scores, candidate_docs, candidate_distances))
            scored.sort(key=lambda x: x[0], reverse=True)

            # Take top_k after reranking
            final = scored[:top_k]  # list of (score, doc, distance)
        else:
            # No reranking: use original distances (lower is better)
            paired = list(zip(candidate_docs, candidate_distances))
            paired.sort(key=lambda x: x[1])  # sort by distance ascending
            final = [(1.0, doc, dist) for doc, dist in paired[:top_k]]  # dummy score

        # 3. Convert to structured format
        retrieved_docs = []
        for score, doc, dist in final:
            if rerank:
                # Use cross-encoder score directly (already in 0..1 range for this model)
                relevance = round(score, 4)
            else:
                # Convert L2 distance to similarity (lower distance → higher similarity)
                relevance = 1 / (1 + dist)
                relevance = round(relevance, 4)

            retrieved_docs.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": relevance,
                    "distance": round(dist, 4),
                    "reranker_score": round(score, 4) if rerank else None,
                }
            )

        return retrieved_docs

    def search_across_doc_types(
        self,
        query: str,
        doc_types: List[str],  # list of doc_type values to search
        top_k: int = 5,
        per_type_k: int = 3,  # how many to retrieve per doc_type
        rerank: bool = True,
    ) -> List[Dict]:
        """
        Search across multiple doc_types, merge results, remove duplicates, then re-rank.

        Args:
            query: The search query
            doc_types: List of document type strings (e.g., ["bank_accounts", "transfer_and_withdraw_fund"])
            top_k: Final number of documents to return
            per_type_k: Number of documents to retrieve from each doc_type (before merging)
            rerank: Whether to apply cross-encoder re-ranking on the merged pool

        Returns:
            List of document dicts with keys: content, metadata, relevance_score, distance, reranker_score (if rerank=True)
        """
        all_candidates = []

        # 1. Search each doc_type individually (without re-ranking to avoid redundant work)
        for dt in doc_types:
            # new: call existing search with filter_metadata, disable reranking for now
            docs = self.search(
                query=query,
                top_k=per_type_k,
                filter_metadata={"doc_type": dt},
                rerank=False,  # we'll re-rank globally after merging
            )
            all_candidates.extend(docs)

        # 2. Remove duplicates based on content (in case a document appears in multiple categories)
        seen_contents = set()
        unique_candidates = []
        for doc in all_candidates:
            content = doc["content"]
            if content not in seen_contents:
                seen_contents.add(content)
                unique_candidates.append(doc)

        # 3. Re-rank the merged pool (if enabled)
        if rerank and unique_candidates:

            reranker = self._get_reranker()
            pairs = [(query, doc["content"]) for doc in unique_candidates]
            scores = reranker.predict(pairs)

            # Add reranker scores to each doc
            for doc, score in zip(unique_candidates, scores):
                doc["reranker_score"] = round(float(score), 4)

            # Sort by reranker score (higher is better)
            unique_candidates.sort(key=lambda x: x["reranker_score"], reverse=True)

            # Take top_k after reranking
            final_docs = unique_candidates[:top_k]

            # Override relevance_score with the reranker score
            for doc in final_docs:
                doc["relevance_score"] = doc["reranker_score"]
        else:
            # No re-ranking: sort by original relevance_score (from L2 distance) and take top_k
            unique_candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
            final_docs = unique_candidates[:top_k]

        return final_docs

    def get_collection_stats(self) -> Dict:
        """Get statistics about the vector store"""

        collection = self.vector_store._collection
        count = collection.count()

        return {
            "total_chunks": count,
            "collection_name": self.collection_name,
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.config["model_name"],
            "dimensions": self.config["dimensions"],
            "chunk_size": self.config["chunk_size"],
        }

    def delete_collection(self):
        """Delete the entire collection (WARNING: Cannot be undone!)"""
        self.vector_store.delete_collection()
        print(f"🗑️ Deleted collection: {self.collection_name}")

    def add_resolved_ticket(
        self, ticket_id: str, question: str, answer: str, metadata: Dict
    ):
        """
        Add successfully resolved ticket to knowledge base.
        """

        doc = Document(
            page_content=f"Question: {question}\n\nAnswer: {answer}",
            metadata={
                "ticket_id": ticket_id,
                "source": "resolved_ticket",
                "issue_type": metadata.get("issue_type"),
                "confidence": metadata.get("confidence"),
                "doc_type": "resolved_ticket",
            },
        )

        self.vector_store.add_documents([doc])

        print(f"✅ Added ticket {ticket_id} to knowledge base")


if __name__ == "__main__":
    vector_store = VectorStoreManager(
        embedding_provider=EmbeddingProvider.SENTENCE_TRANSFORMER
    )
    vector_store.load_and_index_documents()
