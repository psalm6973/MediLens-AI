
from pathlib import Path
from utils.document_processor import extract_document_text

image_folder = Path("data/datasets/ekacare/images")

images = list(image_folder.glob("*.png"))

if not images:
    print("No PNG images found in the dataset folder.")
else:
    image_path = images[1]

    print("Testing image:", image_path.name)
    print("-" * 50)

    try:
        extracted_text = extract_document_text(str(image_path))
        print(extracted_text)
    except Exception as error:
        print("Error:", error)



import pytesseract
from PIL import Image, ImageOps
from pytesseract import Output

image_path = Path("data/datasets/ekacare/images/report_002.png")

image = Image.open(image_path)
image = ImageOps.exif_transpose(image)
image = ImageOps.grayscale(image)

data = pytesseract.image_to_data(
    image,
    lang="eng",
    config="--oem 3 --psm 3",
    output_type=Output.DICT,
)

output_path = Path(
    "data/datasets/ekacare/ocr_results/ocr_confidence.txt"
)

lines = []

for i, word in enumerate(data["text"]):
    word = word.strip()

    if not word:
        continue

    try:
        confidence = float(data["conf"][i])
    except (ValueError, TypeError):
        continue

    lines.append(
        f"Confidence: {confidence:5.1f} | "
        f"Word: {word} | "
        f"Position: ({data['left'][i]}, {data['top'][i]})"
    )

output_path.write_text("\n".join(lines), encoding="utf-8")

print(f"Saved {len(lines)} detected words to {output_path}")
print("Low-confidence words are easier to spot in this file.")


from pathlib import Path

import cv2
import pytesseract

image_path = Path("data/datasets/ekacare/images/report_002.png")
output_folder = Path("data/datasets/ekacare/ocr_results")
output_folder.mkdir(parents=True, exist_ok=True)

image = cv2.imread(str(image_path))

if image is None:
    raise ValueError(f"Could not open image: {image_path}")

height, width = image.shape[:2]

# Experiment: OCR the lower section, excluding the HbA1c graph.
# These proportions are only a starting point for this sample image.
results_region = image[int(height * 0.43):, :]

gray_region = cv2.cvtColor(results_region, cv2.COLOR_BGR2GRAY)

text = pytesseract.image_to_string(
    gray_region,
    lang="eng",
    config="--oem 3 --psm 3",
).strip()

output_path = output_folder / "results_region_psm3.txt"
output_path.write_text(text, encoding="utf-8")

print("\n--- LAB RESULTS REGION ---")
print(text)
print(f"\nSaved to: {output_path}")
