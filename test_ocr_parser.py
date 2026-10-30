
from pathlib import Path
from utils.document_processor import extract_document_text
from utils.report_parser import parse_report_text

# Select a dataset image
IMAGE_PATH = (
    Path(__file__).parent
    / "data"
    / "datasets"
    / "ekacare"
    / "images"
    / "report_002.png"
)

def main():
    print("=" * 60)
    print("MEDILENS-AI: OCR + PARSER TEST")
    print("=" * 60)

    if not IMAGE_PATH.exists():
        print(f"Image not found: {IMAGE_PATH}")
        return

    # STEP 1: OCR
    print("\n[1] Extracting text using OCR...")

    extracted_text = extract_document_text(str(IMAGE_PATH))

    print("\nOCR OUTPUT:")
    print("-" * 60)
    print(extracted_text)

    # STEP 2: PARSING
    print("\n[2] Parsing extracted text...")

    parsed_report = parse_report_text(extracted_text)

    print("\nPARSER RESULTS:")
    print("-" * 60)
    print("Results found:", parsed_report["result_count"])

    for result in parsed_report["results"]:
        print("\nTest:", result["test_name"])
        print("Value:", result["value"])
        print("Unit:", result["unit"])
        print("Reference range:", result["reference_range"])
        print("Flag:", result["flag"])
        print("Needs review:", result["needs_review"])
        print("Reference status:", result["reference_status"])

    # STEP 3: UNPARSED LINES
    print("\nUNPARSED LINES:")
    print("\nUNASSIGNED VALUES:")
    print("-" * 60)

    for item in parsed_report["unassigned_values"]: 
     print(item)
    print("-" * 60)

    for line in parsed_report["unparsed_lines"]:
        print(line)

    # STEP 4: SAVE OUTPUT
    output_path = (
        Path(__file__).parent
        / "data"
        / "datasets"
        / "ekacare"
        / "ocr_results"
        / "report_002_parsed.txt"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        file.write("OCR OUTPUT\n")
        file.write(extracted_text)
        file.write("\n\nPARSER OUTPUT\n")
        file.write(str(parsed_report))

    print("\nSaved output to:", output_path)


if __name__ == "__main__":
    main()
