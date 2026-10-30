
from pathlib import Path
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent

KNOWLEDGE_BASE_PATH = (
    PROJECT_ROOT / "data" / "knowledge_base" / "chroma_db"
)

DOCUMENTS_PATH = (
    PROJECT_ROOT / "data" / "knowledge_base" / "documents"
)

# Embedding model
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

COLLECTION_NAME = "medical_knowledge"


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load and reuse the embedding model."""
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def get_collection():
    """Connect to the local ChromaDB collection."""

    KNOWLEDGE_BASE_PATH.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(KNOWLEDGE_BASE_PATH)
    )

    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Medical reference knowledge"}
    )


def add_documents(
    documents: list[str],
    ids: list[str],
    metadatas: list[dict] | None = None,
):
    """Store medical knowledge and its source information."""

    if len(documents) != len(ids):
        raise ValueError("Each document must have one unique ID.")

    if not documents:
        return

    if any(not document.strip() for document in documents):
        raise ValueError("Documents cannot be empty.")

    if len(set(ids)) != len(ids):
        raise ValueError("Document IDs must be unique.")

    if metadatas is not None and len(metadatas) != len(documents):
        raise ValueError("Each document must have matching metadata.")

    model = get_embedding_model()
    collection = get_collection()

    embeddings = model.encode(documents).tolist()

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def retrieve_documents(
    query: str,
    top_k: int = 3,
) -> list[dict]:
    """Retrieve relevant medical knowledge with source information."""

    if not query.strip():
        raise ValueError("Search query cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    collection = get_collection()

    if collection.count() == 0:
        return []

    model = get_embedding_model()
    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count()),
        include=["documents", "distances", "metadatas"],
    )

    retrieved_documents = []

    for i, document in enumerate(results["documents"][0]):
        retrieved_documents.append({
            "document": document,
            "distance": results["distances"][0][i],
            "metadata": results["metadatas"][0][i],
        })

    return retrieved_documents
