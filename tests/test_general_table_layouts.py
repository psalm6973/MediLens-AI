from utils.report_parser import parse_report_text


REPORT_006 = """
| Date | 22/Dec/2023 09:01AM | 15/Nov/23 09:33AM | 27/Oct/23 09:13AM | 20/Sep/23 08:56AM | 25/Aug/23 07:13AM | Unit | Bio Ref Interval |
|---|---|---|---|---|---|---|---|
| Total Protein Biuret | 6.20 | 6.91 | 6.59 | 5.94 | 6.33 | 7p/6 | 6.6 - 8.3 |
| Albumin Bromcresol Green (BCG) | 3.7 | 4.0 | 3.9 | 3.4 | 3.7 | 7p/6 | 3.5 - 5.2 |
| Globulin Calculated | 2.5 | 3.0 | 2.7 | 2.5 | 2.7 | Ip/6 | 2.3 - 3.5 |
| A.G. ratio Calculated | 1.5 | 1.3 | 1.4 | 1.4 | 1.4 | | 1.2 - 1.5 |
| Bilirubin (Total) DPD | 1.26 | 1.40 | 1.45 | 1.24 | 0.98 | mdl | 0.3 - 1.2 |
| Bilirubin (Direct) Diazotization | 0.29 | 0.31 | 0.33 | 0.31 | 0.25 | mg/dL | 0.0 - 0.2 |
| Bilirubin (Indirect) Calculated | 0.97 | 1.09 | 1.12 | 0.93 | 0.73 | mg/dL | 0.1 - 1.0 |
| SGOT- Aspartate Transaminase (AST) UV without P5P | 32 | 33 | 35 | 37 | 25 | U/L | <50 |
| SGPT- Alanine Transaminase (ALT) UV without P5P | 23 | 19 | 20 | 22 | 13 | U/L | <35 |
| AST/ALT Ratio Calculated | 1.39 | 1.74 | 1.75 | 1.68 | 1.92 | Ratio | |
| Alkaline Phosphatase PNPP, AMP Buffer | 118 | 116 | 128 | 137 | 120 | U/L | 30 - 120 |
| GGTP (Gamma GT), Serum Enzymatic Rate | 42.0 | 45.0 | 44.0 | 54.0 | 48.0 | U/L | 7-50 |
"""


REPORT_007 = """
| MEDICAL EXAMINATION - EYE | RESULTS | LABORATORY INVESTIGATIONS - URINE | RESULTS |
|---|---|---|---|
| R.EYE | 6/6 | SUGAR | ABSENT |
| L.EYE | 6/6 | ALBUMIN | ABSENT |
| EAR | | HEAMOGLOBIN | 13.6mg/dl % |
| LUNGS | NAD | 1.F.B.S | 86mg% |
| ABDOMEN | NAD | 3.CREATININE | 0.7mg% |
"""


def test_historical_table_uses_current_result_and_preserves_history():
    report = parse_report_text(REPORT_006)

    assert report["result_count"] == 12
    total_protein = report["results"][0]
    assert total_protein["test_name"] == "Total Protein Biuret"
    assert total_protein["value"] == 6.20
    assert total_protein["reference_range"] == {
        "type": "range", "low": 6.6, "high": 8.3
    }
    assert len(total_protein["historical_values"]) == 4
    assert total_protein["historical_values"][0]["value"] == 6.91
    assert total_protein["needs_review"] is True  # OCR unit retained, not guessed.


def test_two_side_by_side_result_panels_are_parsed_independently():
    report = parse_report_text(REPORT_007)

    names = [item["test_name"] for item in report["results"]]
    values = [item["value"] for item in report["results"]]

    assert "HEAMOGLOBIN" in names
    assert "1.F.B.S" in names
    assert "3.CREATININE" in names
    assert values == [13.6, 86.0, 0.7]
    assert all(item["needs_review"] for item in report["results"])
    assert report["parser_version"] == "8.0-dynamic-tables"


def test_readable_docling_text_does_not_trigger_tesseract_on_parser_miss(monkeypatch):
    import agents.document_reader as reader
    import utils.docling_processor as docling

    monkeypatch.setattr(
        docling,
        "extract_with_docling",
        lambda _path: "## Clinical Report\nReadable narrative without a result table.",
    )

    def fail_if_fallback_runs(_path):
        raise AssertionError(
            "Tesseract must not run when Docling already returned readable text."
        )

    monkeypatch.setattr(reader, "extract_document_text", fail_if_fallback_runs)

    result = reader.document_reader_agent("dummy-report.png")

    assert result["extraction_method"] == "docling"
    assert result["fallback_attempted"] is False
    assert result["quality_status"] == "parsing_failed"
    assert "Readable narrative" in result["extracted_text"]
