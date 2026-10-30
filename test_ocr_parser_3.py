
from pathlib import Path

from utils.document_processor import extract_document_text
from utils.report_parser import parse_report_text


IMAGE_PATH = (
    Path(__file__).parent
    / "data"
    / "datasets"
    / "ekacare"
    / "images"
    / "report_004.png"
)


def main():
    print("=" * 60)
    print("MEDILENS-AI: CBC REPORT TEST")
    print("=" * 60)

    if not IMAGE_PATH.exists():
        print("Image not found:", IMAGE_PATH)
        return

    print("\n[1] OCR EXTRACTION")

    extracted_text = extract_document_text(str(IMAGE_PATH))
    print(extracted_text)

    print("\n[2] PARSER RESULTS")

    parsed = parse_report_text(extracted_text)

    print("Parser version:", parsed["parser_version"])
    print("Results found:", parsed["result_count"])

    for result in parsed["results"]:
        print("\n", result)

    print("\n[3] UNASSIGNED VALUES")

    for item in parsed["unassigned_values"]:
        print(item)

    print("\n[4] UNPARSED LINES")

    for line in parsed["unparsed_lines"]:
        print(line)


if __name__ == "__main__":
    main()
