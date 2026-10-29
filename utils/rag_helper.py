
from pathlib import Path

import chromadb #import chromadb — imports ChromaDB, our vector database.
from sentence_transformers import SentenceTransformer #from sentence_transformers import SentenceTransformer — imports a model that converts text into numerical representations called embeddings.
#A computer doesn't naturally understand that “high blood sugar” and “elevated glucose” have related meanings. An embedding model converts text into a list of numbers that can help represent its meaning.

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


def get_embedding_model():
    """Load the model used to convert text into embeddings."""
    return SentenceTransformer(EMBEDDING_MODEL_NAME) #SentenceTransformer(EMBEDDING_MODEL_NAME): loads the specified model


def get_collection():
    """Connect to the local ChromaDB collection."""
    KNOWLEDGE_BASE_PATH.mkdir(parents=True, exist_ok=True) #mkdir(): creates a directory. parents=True: creates missing parent directories too.

    client = chromadb.PersistentClient(
        path=str(KNOWLEDGE_BASE_PATH)
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Medical reference knowledge"}
    )

    return collection


def add_documents(documents: list[str], ids: list[str]):
    """Store knowledge documents in ChromaDB."""
    if len(documents) != len(ids):
        raise ValueError("Each document must have one unique ID.")

    if not documents:
        return

    if any(not document.strip() for document in documents):
        raise ValueError("Documents cannot be empty.")

    if len(set(ids)) != len(ids):
        raise ValueError("Document IDs must be unique.")

    model = get_embedding_model()
    collection = get_collection()

    embeddings = model.encode(documents).tolist()

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
    )


def retrieve_documents(query: str, top_k: int = 3) -> list[dict]:
    """Retrieve the most relevant knowledge documents."""
    if not query.strip():
        raise ValueError("Search query cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    model = get_embedding_model()
    collection = get_collection()

    if collection.count() == 0:
        return []

    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count()),
        include=["documents", "distances"],
    )

    retrieved_documents = []

    for i, document in enumerate(results["documents"][0]):
        retrieved_documents.append(
            {
                "document": document,
                "distance": results["distances"][0][i],
            }
        )

    return retrieved_documents
