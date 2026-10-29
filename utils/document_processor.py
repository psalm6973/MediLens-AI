
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, ImageOps


# Tesseract installation on Windows.
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Supported image formats.
SUPPORTED_IMAGE_TYPES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
}

# Selected OCR configuration from our experiments.
OCR_CONFIG = "--oem 3 --psm 3"


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF, using OCR for scanned pages."""
    path = Path(file_path)

    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise ValueError("Please provide a valid PDF file.")

    extracted_pages = []

    with pymupdf.open(path) as document:
        for page in document:
            # First, try extracting selectable PDF text.
            text = page.get_text().strip()

            # If the page has no selectable text, use OCR.
            if not text:
                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(2, 2),
                    alpha=False,
                )

                image = Image.frombytes(
                    "RGB",
                    [pixmap.width, pixmap.height],
                    pixmap.samples,
                )

                image = ImageOps.grayscale(image)

                text = pytesseract.image_to_string(
                    image,
                    lang="eng",
                    config=OCR_CONFIG,
                ).strip()

            if text:
                extracted_pages.append(
                    f"Page {page.number + 1}\n{text}"
                )

    return "\n\n".join(extracted_pages)


def extract_text_from_image(file_path: str) -> str:
    """Extract text from a medical report image using OCR."""
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError("The image file was not found.")

    if path.suffix.lower() not in SUPPORTED_IMAGE_TYPES:
        raise ValueError("Unsupported image format.")

    with Image.open(path) as image:
        # Correct image orientation when metadata is available.
        image = ImageOps.exif_transpose(image)
        image = ImageOps.grayscale(image)

        text = pytesseract.image_to_string(
            image,
            lang="eng",
            config=OCR_CONFIG,
        ).strip()

    return text


def extract_document_text(file_path: str) -> str:
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
