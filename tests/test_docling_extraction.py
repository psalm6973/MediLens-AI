
from pathlib import Path
from docling.document_converter import DocumentConverter


def extract_with_docling(file_path: str) -> str:
    """Extract structured document content using Docling."""

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    converter = DocumentConverter()
    result = converter.convert(str(path))

    return result.document.export_to_markdown()


if __name__ == "__main__":
    report_path = input("Enter your report file path: ").strip().strip('"')

    try:
        extracted_text = extract_with_docling(report_path)

        output_path = Path("docling_output.md")
        output_path.write_text(extracted_text, encoding="utf-8")

        print("\n========== DOCLING EXTRACTION ==========\n")
        print(extracted_text)
        print("\n========================================")
        print(f"\nSaved extraction to: {output_path.resolve()}")

    except Exception as error:
        print(f"\nExtraction failed: {error}")
