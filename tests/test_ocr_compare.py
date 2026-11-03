from pathlib import Path

import pytesseract
from pytesseract import Output
from PIL import Image, ImageOps

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

REPORT_PATH = Path("data/datasets/ekacare/images/report_004.png")

if not REPORT_PATH.exists():
    raise FileNotFoundError(f"Report not found: {REPORT_PATH}")

image = Image.open(REPORT_PATH).convert("RGB")
image = ImageOps.autocontrast(image)

image = image.resize(
    (image.width * 3, image.height * 3),
    Image.Resampling.LANCZOS
)

for psm in [3, 6]:

    print(f"\n{'=' * 20} PSM {psm} {'=' * 20}")

    data = pytesseract.image_to_data(
        image,
        lang="eng",
        config=f"--oem 3 --psm {psm}",
        output_type=Output.DICT
    )

    for i, word in enumerate(data["text"]):

        word = word.strip()

        if not word:
            continue

        try:
            confidence = float(data["conf"][i])
        except ValueError:
            continue

        # Print words that look like numerical results or test names.
        if (
            any(char.isdigit() for char in word)
            or any(term in word.upper() for term in [
                "PROTEIN", "ALBUMIN", "GLOBULIN",
                "BILIRUBIN", "SGOT", "SGPT",
                "PHOSPHATASE", "RATIO"
            ])
        ):
            print(
                f"{word:<18} "
                f"Confidence: {confidence:>5.1f} "
                f"Position: ({data['left'][i]}, {data['top'][i]})"
            )