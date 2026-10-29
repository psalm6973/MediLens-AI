    
from utils.report_parser import parse_report_text


sample = """
Hemoglobin: 13.5 g/dL
Glucose 95 mg/dL
BILIRUBIN, DIRECT 0.35 High < or = 0.30 mg/dL
TOTAL PROTEIN 7.5 6.0 - 8.0 g/dL
"""

parsed = parse_report_text(sample)

print("Results found:", parsed["result_count"])

for result in parsed["results"]:
    print(result)

print("\nUnparsed lines:")
for line in parsed["unparsed_lines"]:
    print(line)
