
from utils.document_processor import extract_document_text
from utils.report_parser import parse_report_text


def _parse_extracted_text(extracted_text: str) -> dict:
    """Parse extracted document text."""
    return parse_report_text(extracted_text)


def _get_results(report: dict) -> list:
    """Safely retrieve parsed test results."""
    if not isinstance(report, dict):
        return []

    return report.get("results", []) or []


def _get_result_count(report: dict) -> int:
    """Get the actual number of parsed results."""
    return len(_get_results(report))


def _check_review_required(report: dict) -> bool:
    """Check whether any extracted result requires verification."""
    return any(
        result.get("needs_review", False)
        for result in _get_results(report)
    )


def document_reader_agent(file_path: str) -> dict:
    """
    Agent 1: Document Reader

    Extraction priority:
        1. Docling
        2. PyMuPDF + Tesseract fallback

    Responsibilities:
        - Extract report content.
        - Parse test results.
        - Preserve original extracted text.
        - Track uncertain values.
        - Avoid silently correcting OCR errors.

    Important:
        A successful extraction does not mean
        medical interpretation is verified.
    """

    warnings = []

    docling_text = ""
    tesseract_text = ""

    docling_report = None
    tesseract_report = None

    extracted_text = ""
    parsed_report = None
    extraction_method = None

    fallback_attempted = False

    # --------------------------------------------------------
    # STEP 1: TRY DOCLING
    # --------------------------------------------------------

    try:
        from utils.docling_processor import extract_with_docling

        print("\n========== DOCLING EXTRACTION ==========")

        docling_text = extract_with_docling(file_path)

        if docling_text and docling_text.strip():

            docling_report = _parse_extracted_text(docling_text)

            docling_count = _get_result_count(docling_report)

            print(
                f"Docling candidate results: {docling_count}",
                flush=True
            )

            if docling_count > 0:
                extracted_text = docling_text
                parsed_report = docling_report
                extraction_method = "docling"

            else:
                warnings.append(
                    "Docling returned content, but no test results "
                    "were identified. Trying Tesseract fallback."
                )

        else:
            warnings.append(
                "Docling returned empty content."
            )

    except Exception as error:

        warnings.append(
            f"Docling extraction failed: {error}"
        )

        print(
            f"Docling failed: {error}",
            flush=True
        )

    # --------------------------------------------------------
    # STEP 2: TESSERACT FALLBACK
    # --------------------------------------------------------

    if parsed_report is None:

        fallback_attempted = True

        print("\n========== TESSERACT FALLBACK ==========")

        try:
            tesseract_text = extract_document_text(file_path)

            if tesseract_text and tesseract_text.strip():

                tesseract_report = _parse_extracted_text(
                    tesseract_text
                )

                tesseract_count = _get_result_count(
                    tesseract_report
                )

                print(
                    f"Tesseract candidate results: {tesseract_count}",
                    flush=True
                )

                if tesseract_count > 0:

                    extracted_text = tesseract_text
                    parsed_report = tesseract_report
                    extraction_method = "tesseract"

                else:
                    warnings.append(
                        "Tesseract extracted text, but no test "
                        "results could be identified."
                    )

            else:
                warnings.append(
                    "Tesseract returned empty content."
                )

        except Exception as error:

            warnings.append(
                f"Tesseract extraction failed: {error}"
            )

            print(
                f"Tesseract failed: {error}",
                flush=True
            )

    # --------------------------------------------------------
    # STEP 3: PRESERVE THE BEST AVAILABLE TEXT
    # --------------------------------------------------------

    if parsed_report is None:

        if docling_report is not None:
            extracted_text = docling_text
            parsed_report = docling_report
            extraction_method = "docling"

        elif tesseract_report is not None:
            extracted_text = tesseract_text
            parsed_report = tesseract_report
            extraction_method = "tesseract"

    # --------------------------------------------------------
    # STEP 4: HANDLE FAILURE
    # --------------------------------------------------------

    if parsed_report is None:

        return {
            "extracted_text": extracted_text,
            "parsed_report": None,
            "extraction_method": extraction_method,
            "extraction_warnings": warnings,
            "fallback_attempted": fallback_attempted,
            "candidate_result_count": 0,
            "review_required": True,
            "quality_status": "extraction_failed",
            "status": "error",
            "error": (
                "Document extraction and parsing could not "
                "produce a usable report."
            ),
        }

    # --------------------------------------------------------
    # STEP 5: CHECK PARSING QUALITY
    # --------------------------------------------------------

    result_count = _get_result_count(parsed_report)

    review_required = (
        result_count == 0
        or _check_review_required(parsed_report)
    )

    if result_count == 0:

        quality_status = "parsing_failed"

        warnings.append(
            "Text was extracted, but no test results "
            "were successfully parsed."
        )

    elif review_required:

        quality_status = "needs_review"

    else:

        quality_status = "candidate_results_found"

    # --------------------------------------------------------
    # STEP 6: LOG SUMMARY
    # --------------------------------------------------------

    print("\n========== DOCUMENT READER SUMMARY ==========")

    print(
        f"Extraction method: {extraction_method}",
        flush=True
    )

    print(
        f"Candidate results: {result_count}",
        flush=True
    )

    print(
        f"Review required: {review_required}",
        flush=True
    )

    print(
        f"Quality status: {quality_status}",
        flush=True
    )

    if warnings:
        print("Warnings:", warnings, flush=True)

    print("==============================================\n")

    # --------------------------------------------------------
    # STEP 7: RETURN TO NEXT AGENT
    # --------------------------------------------------------

    return {
        "extracted_text": extracted_text,
        "parsed_report": parsed_report,
        "extraction_method": extraction_method,
        "extraction_warnings": warnings,
        "fallback_attempted": fallback_attempted,
        "candidate_result_count": result_count,
        "review_required": review_required,
        "quality_status": quality_status,

        # Preserve compatibility with main.py.
        "status": (
            "success"
            if result_count > 0
            else "error"
        ),
    }
