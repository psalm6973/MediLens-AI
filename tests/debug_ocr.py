
from utils.document_processor import extract_document_text

file_path = "data/datasets/ekacare/images/report_004.png"

text = extract_document_text(file_path)

print("\n========== RAW OCR OUTPUT ==========\n")
print(text)
print("\n========== END OF OCR OUTPUT ==========\n")
