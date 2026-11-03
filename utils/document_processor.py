
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, ImageOps


# ============================================================
# 1. CONFIGURATION
# ============================================================

TESSERACT_PATH = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

SUPPORTED_IMAGE_TYPES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
}


# ============================================================
# 2. OCR CANDIDATE
# ============================================================

def _ocr_candidate(image, psm):
    """Run OCR once and return text and confidence information."""

    from pytesseract import Output

    config = f"--oem 3 --psm {psm}"

    data = pytesseract.image_to_data(
        image,
        config=config,
        output_type=Output.DICT
    )

    confidences = []

    for word, confidence in zip(data["text"], data["conf"]):
        word = word.strip()

        if not word:
            continue

        try:
            confidence = float(confidence)

            if confidence >= 0:
                confidences.append(confidence)

        except (TypeError, ValueError):
            pass

    text = pytesseract.image_to_string(
        image,
        config=config
    ).strip()

    average_confidence = (
        sum(confidences) / len(confidences)
        if confidences else 0
    )

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # Small preference for OCR output that preserves rows.
    row_score = min(len(lines), 15) * 1.5

    score = average_confidence + row_score

    return {
        "psm": psm,
        "text": text,
        "confidence": average_confidence,
        "score": score,
        "line_count": len(lines),
    }


# ============================================================
# 3. OCR PROCESSING
# ============================================================

def run_ocr(image):
    """
    Compare multiple OCR layouts and select a readable result.

    No numeric OCR values are automatically corrected.
    """

    image = ImageOps.autocontrast(
        image.convert("L")
    )

    width, height = image.size

    image = image.resize(
        (width * 3, height * 3),
        Image.Resampling.LANCZOS
    )

    candidates = []

    for psm in (3, 6, 11):

        try:
            candidate = _ocr_candidate(image, psm)
            candidates.append(candidate)

            print(
                f"OCR PSM {psm}: "
                f"confidence={candidate['confidence']:.1f}, "
                f"lines={candidate['line_count']}",
                flush=True
            )

        except Exception as error:

            print(
                f"OCR PSM {psm} failed: {error}",
                flush=True
            )

    if not candidates:
        raise RuntimeError(
            "All OCR layout attempts failed."
        )

    best = max(
        candidates,
        key=lambda item: item["score"]
    )

    print(
        f"Selected OCR PSM: {best['psm']}",
        flush=True
    )

    return best["text"]


# ============================================================
# 4. PDF TEXT EXTRACTION
# ============================================================

def extract_pdf_text(file_path):
    """
    Extract selectable PDF text first.

    If a page has no selectable text, use OCR on that page.
    """

    document = pymupdf.open(file_path)

    extracted_pages = []

    try:

        for page_number, page in enumerate(document):

            page_text = page.get_text("text").strip()

            if page_text:
                extracted_pages.append(page_text)

                print(
                    f"Page {page_number + 1}: "
                    "Selectable text extracted.",
                    flush=True
                )

            else:
                print(
                    f"Page {page_number + 1}: "
                    "No selectable text. Running OCR.",
                    flush=True
                )

                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(2, 2),
                    alpha=False
                )

                image = Image.frombytes(
                    "RGB",
                    [pixmap.width, pixmap.height],
                    pixmap.samples
                )

                page_text = run_ocr(image)

                if page_text:
                    extracted_pages.append(page_text)

    finally:
        document.close()

    return "\n\n".join(extracted_pages).strip()


# ============================================================
# 5. IMAGE EXTRACTION
# ============================================================

def extract_image_text(file_path):
    """Extract text from a supported image file."""

    image = Image.open(file_path)

    try:
        image = ImageOps.exif_transpose(image)
        text = run_ocr(image)

    finally:
        image.close()

    return text.strip()


# ============================================================
# 6. MAIN DOCUMENT PROCESSOR
# ============================================================

def extract_document_text(file_path):
    """
    Extract text from a PDF or supported image.

    Returns the original extracted text for the report parser.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Document not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            "The supplied path is not a file."
        )

    extension = path.suffix.lower()

    print(
        f"\nProcessing document: {path.name}",
        flush=True
    )

    if extension == ".pdf":

        extracted_text = extract_pdf_text(path)

    elif extension in SUPPORTED_IMAGE_TYPES:

        extracted_text = extract_image_text(path)

    else:

        raise ValueError(
            f"Unsupported file format: {extension}"
        )

    if not extracted_text.strip():

        raise ValueError(
            "No readable text could be extracted from the document."
        )

    print(
        f"Document extraction completed. "
        f"Characters extracted: {len(extracted_text)}",
        flush=True
    )

    return extracted_text
