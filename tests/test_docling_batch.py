from pathlib import Path

from utils.docling_processor import extract_with_docling
from utils.report_parser import parse_report_text


DATA_DIR = Path("data/datasets")
OUTPUT_DIR = DATA_DIR / "docling_output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

report_files = [
    "APTT.jpg",
    "report-001.jpg",
    "report-002.jpg",
    "report-003.jpg",
    "report-004.png",
    "report-005.jpg",
    "report-006.jpg",
    "report-007.jpg",
    "report-008.jpg",
]

print("\n========== DOCLING BATCH TEST ==========\n")

for filename in report_files:
    file_path = DATA_DIR / filename

    print(f"\n--- {filename} ---")

    if not file_path.exists():
        print("FILE NOT FOUND")
        continue

    try:
        # Step 1: Extract using Docling only
        markdown = extract_with_docling(str(file_path))

        # Save extracted Markdown for inspection
        output_path = OUTPUT_DIR / f"{file_path.stem}.md"
        output_path.write_text(markdown, encoding="utf-8")

        # Step 2: Parse extracted Markdown
        parsed = parse_report_text(markdown)

        results = parsed.get("results", [])
        review_count = sum(
            1 for result in results if result.get("needs_review")
        )

        print("Extraction: SUCCESS")
        print("Parser version:", parsed.get("parser_version"))
        print("Results found:", len(results))
        print("Needs review:", review_count)
        print("Unparsed lines:", len(parsed.get("unparsed_lines", [])))

        for result in results:
            print(
                f"  {result.get('test_name')} | "
                f"Value: {result.get('value')} | "
                f"Review: {result.get('needs_review')}"
            )

    except Exception as error:
        print("EXTRACTION/PARSING FAILED:", error)

print("\n========== BATCH TEST COMPLETE ==========")
