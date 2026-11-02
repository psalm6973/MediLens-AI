
from utils.document_processor import extract_document_text
from utils.report_parser import parse_report_text


file_path = "data/datasets/ekacare/images/report_004.png"

text = extract_document_text(file_path)
report = parse_report_text(text)

print("\n--- PARSER RESULTS ---")

for result in report["results"]:
    print(f"\nTest: {result['test_name']}")
    print(
        f"Primary: {result['value']} "
        f"{result['unit'] or ''}"
    )

    for alternate in result["alternate_values"]:
        print(
            f"Alternate: {alternate['value']} "
            f"{alternate['unit'] or ''}"
        )

    print("Reference:", result["reference_range"])
    print("Flag:", result["flag"])

print("\nTotal tests:", report["result_count"])
print("\nUnparsed lines:", report["unparsed_lines"])
