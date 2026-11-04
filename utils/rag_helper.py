
from pathlib import Path
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

KNOWLEDGE_BASE_PATH = (
    PROJECT_ROOT / "data" / "knowledge_base" / "chroma_db"
)

DOCUMENTS_PATH = (
    PROJECT_ROOT / "data" / "knowledge_base" / "documents"
)

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

COLLECTION_NAME = "medical_knowledge"


# ============================================================
# 2. LOAD AND CACHE MODELS / DATABASE CONNECTIONS
# ============================================================

@lru_cache(maxsize=1)
def get_embedding_model():
    """Load and reuse the embedding model."""

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


@lru_cache(maxsize=1)
def get_chroma_client():
    """Create and reuse the persistent ChromaDB client."""

    KNOWLEDGE_BASE_PATH.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(
        path=str(KNOWLEDGE_BASE_PATH)
    )


@lru_cache(maxsize=1)
def get_collection():
    """Get and reuse the medical knowledge collection."""

    client = get_chroma_client()

    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Medical reference knowledge"}
    )


# ============================================================
# 3. ADD DOCUMENTS
# ============================================================

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

    embeddings = model.encode(
        documents,
        convert_to_numpy=True
    ).tolist()

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )


# ============================================================
# 4. BATCH RETRIEVAL
# ============================================================

def retrieve_documents_batch(
    queries: list[str],
    top_k: int = 2,
) -> list[list[dict]]:
    """
    Retrieve relevant documents for multiple queries
    using a single embedding batch and ChromaDB query.
    """

    if not queries:
        return []

    if any(not isinstance(query, str) or not query.strip()
           for query in queries):
        raise ValueError("Queries cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    collection = get_collection()

    count = collection.count()

    if count == 0:
        return [[] for _ in queries]

    model = get_embedding_model()

    # Generate all query embeddings together.
    query_embeddings = model.encode(
        queries,
        convert_to_numpy=True
    ).tolist()

    # Search all queries in one ChromaDB call.
    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=min(top_k, count),
        include=["documents", "distances", "metadatas"],
    )

    all_retrieved = []

    for query_index, documents in enumerate(results["documents"]):

        retrieved_documents = []

        for document_index, document in enumerate(documents):

            retrieved_documents.append({
                "document": document,
                "distance": results["distances"][query_index][document_index],
                "metadata": results["metadatas"][query_index][document_index],
            })

        all_retrieved.append(retrieved_documents)

    return all_retrieved


# ============================================================
# 5. SINGLE QUERY RETRIEVAL - BACKWARD COMPATIBILITY
# ============================================================

def retrieve_documents(
    query: str,
    top_k: int = 3,
) -> list[dict]:
    """Retrieve relevant medical knowledge for one query."""

    return retrieve_documents_batch(
        [query],
        top_k=top_k
    )[0]
