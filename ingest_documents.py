
from pathlib import Path
import hashlib
import pymupdf

from utils.document_processor import extract_document_text
from utils.rag_helper import add_documents, DOCUMENTS_PATH

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def split_text(text: str) -> list[str]:
    text = " ".join(text.split())

    chunks = []
    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks


def ingest_pdfs():
    pdf_files = list(DOCUMENTS_PATH.rglob("*.pdf"))

    if not pdf_files:
        print("No PDF documents found.")
        return

    all_chunks = []
    all_ids = []
    all_metadata = []

    for pdf_path in pdf_files:
        print(f"\nReading: {pdf_path.name}")

        try:
            # First try normal PDF text extraction
            with pymupdf.open(pdf_path) as document:
                text = "\n".join(
                    page.get_text() for page in document
                ).strip()

            # If no selectable text exists, use OCR
            if not text:
                print("Scanned PDF detected. Using OCR...")
                text = extract_document_text(str(pdf_path))

            chunks = split_text(text)

            if not chunks:
                print("Skipped: No readable text found.")
                continue

            for index, chunk in enumerate(chunks):
                unique_text = f"{pdf_path.name}_{index}_{chunk}"
                chunk_id = hashlib.sha256(
                    unique_text.encode("utf-8")
                ).hexdigest()

                all_chunks.append(chunk)
                all_ids.append(chunk_id)

                all_metadata.append({
                    "source": pdf_path.name,
                    "topic": pdf_path.stem,
                    "chunk": index
                })

            print(f"Extracted {len(chunks)} chunks.")

        except Exception as error:
            print(f"Could not process {pdf_path.name}: {error}")

    if all_chunks:
        add_documents(
            documents=all_chunks,
            ids=all_ids,
            metadatas=all_metadata
        )

    print("\nKnowledge base ingestion completed.")
    print(f"Total chunks stored: {len(all_chunks)}")


if __name__ == "__main__":
    ingest_pdfs()
