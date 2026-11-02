
from agents.document_reader import document_reader_agent
from agents.medical_analysis import medical_analysis_agent
import json


# Use an existing sample report
file_path = "data/datasets/ekacare/images/report_002.png"

print("\nSTEP 1: Reading the medical report...")

reader_output = document_reader_agent(file_path)

print("Document reading completed.")

print("\nSTEP 2: Running medical analysis...")

analysis_output = medical_analysis_agent(
    reader_output["parsed_report"]
)

print("\nSTEP 3: Medical analysis result:\n")

print(json.dumps(analysis_output, indent=4, ensure_ascii=False))

print("\nTEST COMPLETED.")
