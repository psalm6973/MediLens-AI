
from utils.document_processor import extract_document_text
from utils.report_parser import parse_report_text


def document_reader_agent(file_path: str) -> dict:
    """Read a medical report and extract structured results."""

    # Step 1: Extract text from the uploaded document.
    extracted_text = extract_document_text(file_path)

    # Step 2: Parse the extracted text.
    parsed_report = parse_report_text(extracted_text)

    # Step 3: Return the results for the next agent.
    return {
        "extracted_text": extracted_text,
        "parsed_report": parsed_report,
        "status": "success",
    }
