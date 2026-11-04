
from pathlib import Path
from functools import lru_cache

from docling.document_converter import DocumentConverter


@lru_cache(maxsize=1)
def get_converter():
    """
    Create and reuse a Docling converter.
    """
    return DocumentConverter()


def extract_with_docling(file_path: str) -> str:
    """
    Extract structured text and tables from a medical report
    using Docling.

    Returns:
        Extracted document content in Markdown format.

    Raises:
        FileNotFoundError: If the report does not exist.
        ValueError: If Docling produces empty content.
        RuntimeError: If document conversion fails.
    """

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Report file not found: {path}"
        )

    try:
        converter = get_converter()

        result = converter.convert(str(path))

        extracted_text = result.document.export_to_markdown()

        if not extracted_text or not extracted_text.strip():
            raise ValueError(
                "Docling could not extract readable content."
            )

        return extracted_text.strip()

    except ValueError:
        raise

    except Exception as error:
        raise RuntimeError(
            f"Docling extraction failed: {error}"
        ) from error
