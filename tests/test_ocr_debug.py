
from utils.document_processor import extract_document_text

file_path = input("Enter the full path of your APTT report: ").strip().strip('"')

print("\n========== RAW OCR OUTPUT ==========\n")

try:
    extracted_text = extract_document_text(file_path)
    print(extracted_text)

except Exception as error:
    print("OCR ERROR:", type(error).__name__, str(error))

print("\n====================================")
    