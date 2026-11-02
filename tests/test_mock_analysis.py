
from utils.mock_analysis import mock_medical_analysis_agent
from agents.medical_analysis import validate_medical_analysis


sample_report = {
    "results": [
        {
            "test_name": "Hemoglobin",
            "value": "13.5",
            "unit": "g/dL",
            "reference_range": "12-16",
            "original_line": "Hemoglobin: 13.5 g/dL"
        },
        {
            "test_name": "WBC",
            "value": "7500",
            "unit": "cells/uL",
            "reference_range": "4000-11000",
            "original_line": "WBC: 7500 cells/uL"
        }
    ]
}


def test_mock_uses_actual_report_data():
    result = mock_medical_analysis_agent(sample_report)

    assert result["analysis_mode"] == "mock_fallback"
    assert len(result["findings"]) == 2

    assert result["findings"][0]["test_name"] == "Hemoglobin"
    assert result["findings"][0]["reported_value"] == "13.5 g/dL"

    print("PASS: Mock uses actual extracted report data.")


def test_all_findings_require_verification():
    result = mock_medical_analysis_agent(sample_report)

    for finding in result["findings"]:
        assert finding["verification_required"] is True

    print("PASS: All findings require professional verification.")


def test_output_passes_validation():
    result = mock_medical_analysis_agent(sample_report)

    validated_result = validate_medical_analysis(result)

    assert validated_result["status"] == "success"

    print("PASS: Mock output passes Agent 2 validation.")


def test_empty_report():
    result = mock_medical_analysis_agent({"results": []})

    assert result["status"] == "needs_review"
    assert result["findings"] == []
    assert result["analysis_mode"] == "mock_fallback"

    print("PASS: Empty report handled safely.")


if __name__ == "__main__":
    print("\n--- MOCK FALLBACK TESTS ---\n")

    test_mock_uses_actual_report_data()
    test_all_findings_require_verification()
    test_output_passes_validation()
    test_empty_report()

    print("\n--- TESTS COMPLETED ---")
