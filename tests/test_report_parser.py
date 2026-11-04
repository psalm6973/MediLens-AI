
from pathlib import Path

from utils.document_processor import extract_document_text
from utils.report_parser import parse_report_text


def test_report_parser():
    file_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "datasets"
        / "report-004.png"
    )

    assert file_path.exists(), f"Test image not found: {file_path}"

    text = extract_document_text(str(file_path))
    report = parse_report_text(text)

    assert report["results"], "No test results were extracted."

    print("\n--- PARSER RESULTS ---")

    for result in report["results"]:
        print(f"\nTest: {result['test_name']}")
        print(f"Primary: {result['value']} {result['unit'] or ''}")

        for alternate in result["alternate_values"]:
            print(
                f"Alternate: {alternate['value']} "
                f"{alternate['unit'] or ''}"
            )

        print("Reference:", result["reference_range"])
        print("Flag:", result["flag"])

    print("\nTotal tests:", report["result_count"])
    print("\nUnparsed lines:", report["unparsed_lines"])
