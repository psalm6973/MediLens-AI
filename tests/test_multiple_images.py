
import json
from pathlib import Path

from utils.document_processor import extract_document_text
from utils.report_parser import parse_report_text


DATASET_DIR = Path("data/datasets/ekacare/images")
OUTPUT_DIR = Path("test_outputs")
RAW_DIR = OUTPUT_DIR / "raw_ocr"
RESULTS_DIR = OUTPUT_DIR / "parsed_results"

SUPPORTED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg",
    ".tif", ".tiff", ".bmp"
}

# Start with 20 images. Set to None to test all 288.
MAX_IMAGES = 3


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if not DATASET_DIR.exists():
        print(f"Dataset directory not found: {DATASET_DIR}")
        return

    image_files = sorted(
        file for file in DATASET_DIR.rglob("*")
        if file.is_file()
        and file.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    print(f"\nImages discovered: {len(image_files)}")

    if MAX_IMAGES is not None:
        image_files = image_files[:MAX_IMAGES]

    print(f"Images selected for testing: {len(image_files)}")

    summary = []

    for index, image_path in enumerate(image_files, start=1):
        print(f"\n[{index}/{len(image_files)}] {image_path.name}")

        try:
            # OCR extraction
            extracted_text = extract_document_text(str(image_path))

            # Save raw OCR
            raw_path = RAW_DIR / f"{image_path.stem}_raw.txt"
            raw_path.write_text(extracted_text, encoding="utf-8")

            # Parse extracted text
            parsed = parse_report_text(extracted_text)
            results = parsed.get("results", [])

            # Save complete parsed output
            parsed_path = RESULTS_DIR / f"{image_path.stem}_parsed.json"
            parsed_path.write_text(
                json.dumps(parsed, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8"
            )

            status = parsed.get("status", "unknown")

            summary.append({
                "image": str(image_path.relative_to(DATASET_DIR)),
                "status": status,
                "candidate_count": len(results),
                "error": ""
            })

            print(f"Status: {status}")
            print(f"Candidates: {len(results)}")

            for item in results:
                print(
                    f"  - {item.get('test_name', 'Unknown')}: "
                    f"{item.get('value')} {item.get('unit') or ''} "
                    f"| Review: {item.get('needs_review')}"
                )

        except Exception as error:
            print(f"ERROR: {error}")

            summary.append({
                "image": str(image_path.relative_to(DATASET_DIR)),
                "status": "error",
                "candidate_count": 0,
                "error": str(error)
            })

    # Save summary
    summary_path = OUTPUT_DIR / "batch_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    successful = sum(
        item["status"] != "error" for item in summary
    )
    failed = len(summary) - successful

    print("\n" + "=" * 60)
    print("BATCH TEST SUMMARY")
    print("=" * 60)
    print(f"Images tested: {len(summary)}")
    print(f"Completed: {successful}")
    print(f"Errors: {failed}")
    print(f"Summary: {summary_path}")
    print(f"Raw OCR: {RAW_DIR}")
    print(f"Parsed results: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
