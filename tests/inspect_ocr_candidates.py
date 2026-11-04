from pathlib import Path

from PIL import Image, ImageOps

from utils.document_processor import _ocr_candidate


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REPORTS = [
    PROJECT_ROOT / "data" / "datasets" / "APTT.jpg",
    PROJECT_ROOT /"data"/"datasets" / "ekacare" / "images" / "report_004.png",
]


def inspect_report(file_path):
    print("\n" + "=" * 80)
    print(f"REPORT: {file_path.name}")
    print("=" * 80)

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    image = Image.open(file_path)

    try:
        image = ImageOps.autocontrast(image.convert("L"))

        width, height = image.size
        image = image.resize(
            (width * 3, height * 3),
            Image.Resampling.LANCZOS
        )

        for psm in (3, 6, 11):
            print(f"\n{'-' * 30} PSM {psm} {'-' * 30}")

            try:
                result = _ocr_candidate(image, psm)

                print(f"Confidence: {result['confidence']:.2f}")
                print(f"Lines: {result['line_count']}")
                print("\nOCR TEXT:\n")
                print(result["text"])

            except Exception as error:
                print(f"PSM {psm} failed: {error}")

    finally:
        image.close()


if __name__ == "__main__":
    for report in REPORTS:
        inspect_report(report)