
import json

from agents.medical_analysis import medical_analysis_agent


# ============================================================
# REPORT 1: URINE PROTEIN CREATININE RATIO
# ============================================================

urine_report = {
    "results": [
        {
            "test_name": "Urine Protein",
            "value": 260,
            "raw_ocr_value": "260",
            "unit": "mg/dL",
            "raw_ocr_unit": "mg/dL",
            "reference_range": "Not established",
            "reference_status": "unknown",
            "flag": None,
            "needs_review": True,
            "alternate_values": [],
            "original_line": "Urine Protein 260 mg/dL"
        },
        {
            "test_name": "Urine Creatinine",
            "value": 201.11,
            "raw_ocr_value": "201.11",
            "unit": "mg/dL",
            "raw_ocr_unit": "mg/dL",
            "reference_range": {
                "type": "range",
                "low": 16,
                "high": 327
            },
            "reference_status": "normal",
            "flag": None,
            "needs_review": True,
            "alternate_values": [],
            "original_line": "Urine Creatinine 201.11 mg/dL"
        },
        {
            "test_name": "Protein Creatinine Ratio",
            "value": 1.29,
            "raw_ocr_value": "1.29",
            "unit": "",
            "raw_ocr_unit": "",
            "reference_range": {
                "type": "range",
                "low": 0,
                "high": 0.2
            },
            "reference_status": "high",
            "flag": None,
            "needs_review": True,
            "alternate_values": [],
            "original_line": "Protein Creatinine Ratio 1.29"
        }
    ]
}


# ============================================================
# REPORT 2: COAGULATION PROFILE
# ============================================================

aptt_report = {
    "results": [
        {
            "test_name": "APTT",
            "value": 31.9,
            "raw_ocr_value": "31.9",
            "unit": "Seconds",
            "raw_ocr_unit": "Seconds",
            "reference_range": {
                "type": "range",
                "low": 27.6,
                "high": 35.9
            },
            "reference_status": "normal",
            "flag": None,
            "needs_review": True,
            "alternate_values": [],
            "original_line": "APTT 31.9 Seconds"
        },
        {
            "test_name": "MNAPTT",
            "value": 31.7,
            "raw_ocr_value": "31.7",
            "unit": "Seconds",
            "raw_ocr_unit": "Seconds",
            "reference_range": None,
            "reference_status": "unknown",
            "flag": None,
            "needs_review": True,
            "alternate_values": [],
            "original_line": "MNAPTT 31.7 Seconds"
        }
    ]
}


# ============================================================
# RUN BOTH REPORTS
# ============================================================

def run_test(report_name, report_data):

    print(f"\n{'=' * 55}")
    print(f"TESTING: {report_name}")
    print(f"{'=' * 55}")

    result = medical_analysis_agent(report_data)

    print("\nANALYSIS RESULT:")
    print(json.dumps(result, indent=4))

    print("\nAnalysis mode:", result.get("analysis_mode"))
    print("Number of findings:", len(result.get("findings", [])))

    print(f"\nFINISHED: {report_name}")
    print("=" * 55)

    return result


if __name__ == "__main__":

    urine_result = run_test(
        "Urine Protein Creatinine Ratio",
        urine_report
    )

    aptt_result = run_test(
        "APTT Coagulation Profile",
        aptt_report
    )
