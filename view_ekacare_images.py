
from datasets import load_from_disk
from pathlib import Path

dataset_path = Path(
    "data/datasets/ekacare/huggingface_dataset"
)

output_folder = Path(
    "data/datasets/ekacare/images"
)
output_folder.mkdir(parents=True, exist_ok=True)

dataset = load_from_disk(str(dataset_path))

print("Total records:", len(dataset))
print("Columns:", dataset.column_names)

for index, record in enumerate(dataset):
    image = record["image"]

    if image is None:
        continue

    image_path = output_folder / f"report_{index + 1:03d}.png"
    image.convert("RGB").save(image_path)

print("Images saved to:", output_folder.resolve())
