from pathlib import Path
import pytesseract
from PIL import Image, ImageOps

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

REPORT_PATH = Path("data/datasets/ekacare/images/report_004.png")

image = Image.open(REPORT_PATH).convert("RGB")
image = ImageOps.autocontrast(image)

w, h = image.size

# Crop the report's table area
crop = image.crop((
    int(w * 0.02),
    int(h * 0.40),
    int(w * 0.99),
    int(h * 0.85)
))

# Enlarge the cropped table
crop = crop.resize(
    (crop.width * 2, crop.height * 2),
    Image.Resampling.LANCZOS
)

for psm in [3, 4, 6, 11]:
    print(f"\n{'=' * 15} PSM {psm} {'=' * 15}")

    text = pytesseract.image_to_string(
        crop,
        lang="eng",
        config=f"--oem 3 --psm {psm}"
    )

    print(text)