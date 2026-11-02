
from utils.document_processor import extract_document_text
from utils.report_parser import parse_report_text


def document_reader_agent(file_path: str) -> dict:
    """
    Read a medical report and extract structured result candidates.

    OCR output is preserved so later agents can inspect the original
    extracted text when structured parsing is incomplete.
    """

    # Step 1: Extract text from the uploaded document.
    extracted_text = extract_document_text(file_path)

    print("\n========== OCR EXTRACTED TEXT ==========")
    print(extracted_text)
    print("========================================\n")

    # Step 2: Parse candidate test results.
    parsed_report = parse_report_text(extracted_text)

    print(
        "Extracted candidate results:",
        parsed_report["result_count"],
    )

    # Step 3: Return both original text and parsed candidates.
    return {
        "extracted_text": extracted_text,
        "parsed_report": parsed_report,
        "status": (
            "success"
            if parsed_report["result_count"] > 0
            else "needs_review"
        ),
    }
