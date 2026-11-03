import json
from agents.medical_analysis import medical_analysis_agent


# Report 4: Liver Profile
# Values transcribed from the report details previously provided.

sample_report = {
    "results": [
        {
            "test_name": "Total Protein",
            "value": 6.80,
            "raw_ocr_value": "6.80",
            "unit": "g/dL",
            "raw_ocr_unit": "g/dL",
            "reference_range": {"type": "range", "low": 6.70, "high": 8.20},
            "reference_status": "normal",
            "flag": None,
            "needs_review": True,
            "alternate_values": [
                {
                    "value": 68.00,
                    "raw_ocr_value": "68.00",
                    "unit": "g/L",
                    "raw_ocr_unit": "g/L",
                    "reference_range": {"type": "range", "low": 67, "high": 82},
                    "needs_review": True,
                    "original_line": "Total Protein 68.00 g/L"
                }
            ],
            "original_line": "Total Protein 6.80 g/dL"
        },
        {
            "test_name": "Albumin",
            "value": 2.80,
            "raw_ocr_value": "2.80",
            "unit": "g/dL",
            "raw_ocr_unit": "g/dL",
            "reference_range": {"type": "range", "low": 3.50, "high": 5.00},
            "reference_status": "low",
            "flag": "L",
            "needs_review": True,
            "alternate_values": [
                {
                    "value": 28.00,
                    "raw_ocr_value": "28.00",
                    "unit": "g/L",
                    "raw_ocr_unit": "g/L",
                    "reference_range": {"type": "range", "low": 35, "high": 50},
                    "needs_review": True,
                    "original_line": "Albumin 28.00 g/L"
                }
            ],
            "original_line": "Albumin 2.80 g/dL"
        },
        {
            "test_name": "Globulin",
            "value": 4.00,
            "raw_ocr_value": "4.00",
            "unit": "g/dL",
            "raw_ocr_unit": "g/dL",
            "reference_range": {"type": "range", "low": 2.60, "high": 4.10},
            "reference_status": "normal",
            "flag": None,
            "needs_review": True,
            "alternate_values": [
                {
                    "value": 40.00,
                    "raw_ocr_value": "40.00",
                    "unit": "g/L",
                    "raw_ocr_unit": "g/L",
                    "reference_range": {"type": "range", "low": 26, "high": 41},
                    "needs_review": True,
                    "original_line": "Globulin 40.00 g/L"
                }
            ],
            "original_line": "Globulin 4.00 g/dL"
        },
        {
            "test_name": "A/G Ratio",
            "value": 0.70,
            "raw_ocr_value": "0.70",
            "unit": "",
            "raw_ocr_unit": "",
            "reference_range": {"type": "range", "low": 1.20, "high": 2.50},
            "reference_status": "low",
            "flag": "L",
            "needs_review": True,
            "alternate_values": [],
            "original_line": "A/G Ratio 0.70"
        },
        {
            "test_name": "Total Bilirubin",
            "value": 0.80,
            "raw_ocr_value": "0.80",
            "unit": "mg/dL",
            "raw_ocr_unit": "mg/dL",
            "reference_range": {"type": "range", "low": 0.20, "high": 1.00},
            "reference_status": "normal",
            "flag": None,
            "needs_review": True,
            "alternate_values": [
                {
                    "value": 13.68,
                    "raw_ocr_value": "13.68",
                    "unit": "umol/L",
                    "raw_ocr_unit": "umol/L",
                    "reference_range": {"type": "range", "low": 3.42, "high": 17.10},
                    "needs_review": True,
                    "original_line": "Total Bilirubin 13.68 umol/L"
                }
            ],
            "original_line": "Total Bilirubin 0.80 mg/dL"
        },
        {
            "test_name": "SGOT",
            "value": 38.00,
            "raw_ocr_value": "38.00",
            "unit": "U/L",
            "raw_ocr_unit": "U/L",
            "reference_range": {"type": "range", "low": 9, "high": 36},
            "reference_status": "high",
            "flag": "H",
            "needs_review": True,
            "alternate_values": [],
            "original_line": "SGOT 38.00 U/L"
        },
        {
            "test_name": "SGPT",
            "value": 76.00,
            "raw_ocr_value": "76.00",
            "unit": "U/L",
            "raw_ocr_unit": "U/L",
            "reference_range": {"type": "range", "low": 10, "high": 40},
            "reference_status": "high",
            "flag": "H",
            "needs_review": True,
            "alternate_values": [],
            "original_line": "SGPT 76.00 U/L"
        },
        {
            "test_name": "Alkaline Phosphatase",
            "value": 128.00,
            "raw_ocr_value": "128.00",
            "unit": "U/L",
            "raw_ocr_unit": "U/L",
            "reference_range": {"type": "range", "low": 40, "high": 120},
            "reference_status": "high",
            "flag": "H",
            "needs_review": True,
            "alternate_values": [],
            "original_line": "Alkaline Phosphatase 128.00 U/L"
        }
    ]
}


result = medical_analysis_agent(sample_report)

print("\n========== REPORT 4 ANALYSIS ==========\n")
print(json.dumps(result, indent=4))
print("\nAnalysis mode:", result.get("analysis_mode"))
print("Number of findings:", len(result.get("findings", [])))
print("\n=======================================\n")
