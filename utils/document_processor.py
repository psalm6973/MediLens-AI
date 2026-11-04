
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, ImageOps

from pytesseract import Output
from utils.ocr_selector import select_psm, score_ocr_candidate


pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

SUPPORTED_IMAGE_TYPES = {
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"
}

PSM_MODES = (3, 6, 11)


def prepare_image(image):
    """Prepare an image consistently for OCR."""

    image = ImageOps.exif_transpose(image)
    image = ImageOps.autocontrast(image.convert("L"))

    width, height = image.size

    return image.resize(
        (width * 3, height * 3),
        Image.Resampling.LANCZOS
    )


def get_ocr_confidence(image, psm):
    """Calculate average confidence for recognized words."""

    data = pytesseract.image_to_data(
        image,
        lang="eng",
        config=f"--oem 3 --psm {psm}",
        output_type=Output.DICT
    )

    values = []

    for word, confidence in zip(data["text"], data["conf"]):
        if not word.strip():
            continue

        try:
            confidence = float(confidence)
            if confidence >= 0:
                values.append(confidence)
        except (TypeError, ValueError):
            continue

    return sum(values) / len(values) if values else 0.0


def run_ocr(image):
    """Compare multiple OCR layouts and select the strongest candidate."""

    prepared = prepare_image(image)

    # Layout analysis is retained as supporting information.
    suggested_psm, reason = select_psm(prepared)

    print(
        f"Layout suggestion: PSM {suggested_psm} ({reason})",
        flush=True
    )

    candidates = []

    for psm in PSM_MODES:
        try:
            text = pytesseract.image_to_string(
                prepared,
                lang="eng",
                config=f"--oem 3 --psm {psm}"
            ).strip()

            confidence = get_ocr_confidence(prepared, psm)

            score, metrics = score_ocr_candidate(
                text,
                confidence
            )

            candidates.append({
                "psm": psm,
                "text": text,
                "score": score,
                "metrics": metrics,
            })

            print(
                f"PSM {psm}: score={score:.2f}, "
                f"metrics={metrics}",
                flush=True
            )

        except Exception as error:
            print(f"PSM {psm} failed: {error}", flush=True)

    if not candidates:
        raise RuntimeError("All OCR candidates failed.")

    best = max(candidates, key=lambda item: item["score"])

    print(
        f"Selected PSM: {best['psm']} "
        f"(score={best['score']:.2f})",
        flush=True
    )

    return best["text"]


def extract_text_from_pdf(file_path):
    """Extract selectable text or OCR scanned PDF pages."""

    path = Path(file_path)

    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise ValueError("Please provide a valid PDF file.")

    extracted_pages = []

    with pymupdf.open(path) as document:
        for page in document:
            text = page.get_text("text").strip()

            if not text:
                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(2, 2),
                    alpha=False
                )

                image = Image.frombytes(
                    "RGB",
                    [pixmap.width, pixmap.height],
                    pixmap.samples
                )

                try:
                    text = run_ocr(image)
                finally:
                    image.close()

            if text:
                extracted_pages.append(
                    f"Page {page.number + 1}\n{text}"
                )

    return "\n\n".join(extracted_pages)


def extract_text_from_image(file_path):
    """Extract text from a medical report image."""

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError("The image file was not found.")

    if path.suffix.lower() not in SUPPORTED_IMAGE_TYPES:
        raise ValueError("Unsupported image format.")

    with Image.open(path) as original_image:
        image = ImageOps.exif_transpose(original_image)
        return run_ocr(image)


def extract_document_text(file_path):
    """Extract text from a supported medical document."""

    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".pdf":
        text = extract_text_from_pdf(str(path))

    elif extension in SUPPORTED_IMAGE_TYPES:
        text = extract_text_from_image(str(path))

    else:
        raise ValueError(
            "Supported files: PDF, PNG, JPG, JPEG, TIF, TIFF, BMP."
        )

    if not text.strip():
        raise ValueError(
            "No readable text was found. Try a clearer scan or image."
        )

    return text
