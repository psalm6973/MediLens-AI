
from pathlib import Path
from utils.document_processor import extract_document_text

image_folder = Path("data/datasets/ekacare/images")
output_folder = Path("data/datasets/ekacare/ocr_results")

output_folder.mkdir(parents=True, exist_ok=True)

extensions = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

images = sorted(
    path for path in image_folder.iterdir()
    if path.suffix.lower() in extensions
)[:5]

if not images:
    print("No supported images found.")
else:
    for image_path in images:
        print(f"\nProcessing: {image_path.name}")

        try:
            text = extract_document_text(str(image_path))

            output_path = output_folder / f"{image_path.stem}.txt"
            output_path.write_text(text, encoding="utf-8")

            print("Extracted characters:", len(text))
            print("Saved to:", output_path)

        except Exception as error:
            print("Failed:", error)

    print("\nBatch OCR test completed.")
