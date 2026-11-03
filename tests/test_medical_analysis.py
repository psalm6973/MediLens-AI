
from pathlib import Path
from agents.document_reader import document_reader_agent
from agents.medical_analysis import medical_analysis_agent


# ============================================================
# REPORT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REPORTS = {
    "APTT Coagulation Profile": (
        PROJECT_ROOT / "data" / "datasets" / "APTT.jpg"
    ),

    "Liver Profile Report 4": (
        PROJECT_ROOT / "data"/ "datasets" / "ekacare" / "images"
        / "report_004.png"
    ),
}


# ============================================================
# TEST BOTH REPORTS
# ============================================================

for report_name, report_path in REPORTS.items():

    print("\n" + "=" * 65)
    print(f"TESTING: {report_name}")
    print("=" * 65)

    if not report_path.exists():
        print(f"ERROR: Report not found: {report_path}")
        continue

    try:

        # STEP 1: DOCUMENT READER + OCR + PARSER
        document_result = document_reader_agent(
            str(report_path)
        )

        print("\n---------- OCR TEXT ----------")
        print(document_result["extracted_text"])

        parsed_report = document_result["parsed_report"]

        print("\n---------- PARSED RESULTS ----------")
        print(f"Result count: {parsed_report['result_count']}")

        for item in parsed_report["results"]:
            print({
                "test_name": item.get("test_name"),
                "value": item.get("value"),
                "raw_ocr_value": item.get("raw_ocr_value"),
                "unit": item.get("unit"),
                "reference_range": item.get("reference_range"),
                "reference_status": item.get("reference_status"),
                "flag": item.get("flag"),
                "needs_review": item.get("needs_review"),
                "alternate_values": item.get("alternate_values"),
            })

        # STEP 2: GROQ + RAG MEDICAL ANALYSIS
        analysis = medical_analysis_agent(parsed_report)

        print("\n---------- MEDICAL ANALYSIS ----------")
        print(analysis)

        print("\nAnalysis mode:", analysis.get("analysis_mode"))
        print("Analysis status:", analysis.get("status"))

    except Exception as error:

        print(f"\nERROR while testing {report_name}:")
        print(f"{type(error).__name__}: {error}")


print("\n" + "=" * 65)
print("BOTH REPORT TESTS COMPLETED")
print("=" * 65)
