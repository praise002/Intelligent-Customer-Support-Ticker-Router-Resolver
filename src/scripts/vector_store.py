import json
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

        print(f"📦 Vector store initialized with {self.embedding_provider} embeddings")

    def _auto_detect_provider(self) -> EmbeddingProvider:
        """
        Auto-detect which embedding provider to use based on available API keys.


        """
        nvidia_key = config("NVIDIA_API_KEY", default=None)
        openai_key = config("OPENAI_API_KEY", default=None)

        if nvidia_key:
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
        self, query: str, top_k: int = 5, filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """Search for documents similar to query."""

        if filter_metadata:
            results = self.vector_store.similarity_search_with_score(
                query=query, k=top_k, filter=filter_metadata
            )
        else:
            results = self.vector_store.similarity_search_with_score(
                query=query, k=top_k
            )

        # Convert to structured format
        retrieved_docs = []
        for doc, distance in results:
            # Convert L2 distance to similarity score (0-1)
            # Lower distance = higher similarity
            similarity = 1 / (1 + distance)

            retrieved_docs.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": round(similarity, 4),
                    "distance": round(distance, 4),
                }
            )

        return retrieved_docs

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
