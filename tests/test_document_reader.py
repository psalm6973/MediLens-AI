
from agents.document_reader import document_reader_agent

file_path = "data/datasets/ekacare/images/report_002.png"

result = document_reader_agent(file_path)

print("Status:", result["status"])
print("\nParsed Results:")

for item in result["parsed_report"]["results"]:
    print(item)
