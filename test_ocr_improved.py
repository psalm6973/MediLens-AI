
from pathlib import Path

import cv2
import pytesseract

from utils.document_processor import extract_document_text


# Use the same Tesseract installation as our project.
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

image_folder = Path("data/datasets/ekacare/images")
output_folder = Path("data/datasets/ekacare/ocr_results")
output_folder.mkdir(parents=True, exist_ok=True)

images = sorted(image_folder.glob("*.png"))

if not images:
    raise FileNotFoundError(
        "No PNG images found in the dataset folder."
    )

image_path = images[0]
image = cv2.imread(str(image_path))

if image is None:
    raise ValueError(f"Could not open image: {image_path}")

print(f"Testing image: {image_path.name}")

# 1. Existing project OCR.
original_text = extract_document_text(str(image_path))

(output_folder / "original.txt").write_text(
    original_text,
    encoding="utf-8",
)

# 2. Enlarge the image and improve local contrast.
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

gray = cv2.resize(
    gray,
    None,
    fx=2,
    fy=2,
    interpolation=cv2.INTER_CUBIC,
)

enhanced = cv2.createCLAHE(
    clipLimit=2.0,
    tileGridSize=(8, 8),
).apply(gray)

# 3. Create a thresholded version.
thresholded = cv2.adaptiveThreshold(
    enhanced,
    255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY,
    31,
    11,
)

# 4. Compare different preprocessing and page segmentation modes.
variants = {
    "original_psm3": (image, "--oem 3 --psm 3"),
    "original_psm4": (image, "--oem 3 --psm 4"),
    "original_psm6": (image, "--oem 3 --psm 6"),
    "enhanced_psm3": (enhanced, "--oem 3 --psm 3"),
    "enhanced_psm4": (enhanced, "--oem 3 --psm 4"),
    "enhanced_psm6": (enhanced, "--oem 3 --psm 6"),
    "thresholded_psm3": (thresholded, "--oem 3 --psm 3"),
    "thresholded_psm4": (thresholded, "--oem 3 --psm 4"),
    "thresholded_psm6": (thresholded, "--oem 3 --psm 6"),
}

# Final check: does enlarging the original image help?
original_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

resized_gray = cv2.resize(
    original_gray,
    None,
    fx=2,
    fy=2,
    interpolation=cv2.INTER_CUBIC,
)

resized_text = pytesseract.image_to_string(
    resized_gray,
    lang="eng",
    config="--oem 3 --psm 3",
).strip()

(output_folder / "resized_original_psm3.txt").write_text(
    resized_text,
    encoding="utf-8",
)

print(
    f"resized_original_psm3: {len(resized_text)} characters"
)

results = []

for name, (processed_image, config) in variants.items():
    text = pytesseract.image_to_string(
        processed_image,
        lang="eng",
        config=config,
    ).strip()

    (output_folder / f"{name}.txt").write_text(
        text,
        encoding="utf-8",
    )

    results.append((name, len(text)))

    print(f"{name}: {len(text)} characters")

# Save processed images for visual inspection.
cv2.imwrite(str(output_folder / "enhanced.png"), enhanced)
cv2.imwrite(str(output_folder / "thresholded.png"), thresholded)

# Print a summary for quick comparison.
print("\n--- OCR COMPARISON ---")
for name, character_count in results:
    print(f"{name:<22} {character_count:>5} characters")

print("\nExperiment completed.")
print("Results saved in:", output_folder.resolve())
