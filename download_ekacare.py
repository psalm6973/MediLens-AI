
from datasets import load_dataset

print("Loading EkaCare dataset...")

dataset = load_dataset(
    "ekacare/medical_records_parsing_validation_set",
    split="test",
)

print("Number of records:", len(dataset))
print("Available columns:", dataset.column_names)

dataset.save_to_disk(
    "data/datasets/ekacare/huggingface_dataset"
)

print("Dataset downloaded and saved successfully!")
