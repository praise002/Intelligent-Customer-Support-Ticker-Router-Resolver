import json
import os
from pathlib import Path
from typing import Dict, List

from decouple import config
from langchain_chroma import Chroma
from langchain_classic.schema import Document
from langchain_core.documents import Document
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


class VectorStoreManager:
    def __init__(
        self,
        collection_name: str = "stripe_docs",
        persist_directory: str = "data/chroma_db",
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.model_name_nv = "nvidia/nv-embed-v1"
        self.model_name_s = "all-MiniLM-L6-v2"

        # Try NVIDIA embeddings first, fallback to SentenceTransformer
        nvidia_api_key = os.environ.get("NVIDIA_API_KEY") or config("NVIDIA_API_KEY_2", default=None)
        
        if nvidia_api_key:
            # NVIDIA API key found - use it!
            print("✅ Using NVIDIA embeddings (nv-embed-v1)")
            os.environ["NVIDIA_API_KEY"] = nvidia_api_key
            self.embeddings = NVIDIAEmbeddings(
                model="nvidia/nv-embed-v1",
                truncate="END"
            )
            self.embedding_provider = "nvidia"
        else:
            # No NVIDIA key - fallback to local embeddings
            print("⚠️ NVIDIA_API_KEY not found. Falling back to SentenceTransformer (local).")
            from langchain_community.embeddings import SentenceTransformerEmbeddings
            
            self.embeddings = SentenceTransformerEmbeddings(
                model_name="all-MiniLM-L6-v2"
            )
            self.embedding_provider = "local"

        # Initialize Chroma vector store
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(self.persist_directory),
        )
        
        print(f"📦 Vector store initialized with {self.embedding_provider} embeddings")

    def _load_documents_from_json(self, docs_file: str) -> List[Document]:
        """Load documents from JSON and convert to LangChain Documents"""

        with open(docs_file, "r", encoding="utf-8") as f:
            docs_data = json.load(f)

        print(f"Loading {len(docs_data)} documents from {docs_file}")

        # Convert to LangChain Document objects
        documents = []
        for doc in docs_data:
            # Create Document with page_content and metadata
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

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,  # measured in tokens
            chunk_overlap=200,
            add_start_index=True,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        
        # For sentence transformer
        # text_splitter = RecursiveCharacterTextSplitter(
        #     chunk_size=341,  # measured in tokens
        #     chunk_overlap=80,
        #     add_start_index=True,
        #     separators=["\n\n", "\n", ". ", " ", ""],
        # )

        print("Splitting documents into chunks...")
        splits = text_splitter.split_documents(documents)
        print(f"Created {len(splits)} chunks from {len(documents)} documents")

        return splits

    def load_and_index_documents(
        self, docs_file: str = "data/stripe_docs/stripe_docs.json"
    ):
        """Load documents from JSON and index them in vector store"""

        # Load documents
        documents = self._load_documents_from_json(docs_file)

        # Split into chunks
        all_splits = self._split_documents(documents)

        # Add to vector store (LangChain handles embedding automatically!)
        print("Adding documents to vector store...")
        print("(NVIDIA embeddings will be generated automatically)")

        ids = self.vector_store.add_documents(documents=all_splits)

        print(f"✅ Indexed {len(ids)} document chunks successfully!")

        return len(ids)

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant documents"""

        # LangChain's similarity_search automatically:
        # 1. Embeds the query using self.embeddings
        # 2. Searches ChromaDB
        # 3. Returns Document objects
        results = self.vector_store.similarity_search_with_score(query=query, k=top_k)

        # Convert to our format
        retrieved_docs = []
        for doc, score in results:
            # Convert distance to similarity (ChromaDB returns L2 distance)
            # Lower distance = higher similarity
            similarity = 1 / (1 + score)

            retrieved_docs.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": similarity,
                }
            )

        return retrieved_docs

    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection"""

        # Get collection from vector store
        collection = self.vector_store._collection
        count = collection.count()

        return {
            "total_chunks": count,
            "collection_name": self.collection_name,
            "embedding_model": self.model_name_nv,
        }

    def delete_collection(self):
        """Delete the entire collection (use with caution!)"""
        self.vector_store.delete_collection()
        print(f"🗑️ Deleted collection: {self.collection_name}")


if __name__ == "__main__":
    # Initialize vector store manager
    vs_manager = VectorStoreManager()

    # Check if already indexed
    stats = vs_manager.get_collection_stats()

    if stats["total_chunks"] == 0:
        print("Vector store is empty. Indexing documents...")
        vs_manager.load_and_index_documents()
    else:
        print(f"Vector store already contains {stats['total_chunks']} chunks")
        print(f"Using embedding model: {stats['embedding_model']}")

    # Test search
    test_query = "API key not working"
    print(f"\n🔍 Test search: '{test_query}'")
    results = vs_manager.search(test_query, top_k=3)

    for i, doc in enumerate(results, 1):
        print(f"\n{i}. Relevance: {doc['relevance_score']:.3f}")
        print(f"   Source: {doc['metadata']['title']}")
        print(f"   Content: {doc['content'][:150]}...")

# NOTE: By default, input text longer than 256 word pieces is truncated.
# fOR SENTENCE TRANSFORMER
# 341 tokens