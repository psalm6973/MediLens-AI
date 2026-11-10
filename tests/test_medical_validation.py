from copy import deepcopy

import pytest

from agents.medical_analysis import validate_medical_analysis


VALID_ANALYSIS = {
    "status": "success",
    "summary": "The report contains sample test results.",
    "findings": [
        {
            "test_name": "Sample Test",
            "reported_value": "10",
            "meaning": "A sample explanation.",
            "observation": "Interpret in clinical context.",
            "verification_required": True,
            "source": None,
        }
    ],
    "general_guidance": [
        "Discuss the report with a qualified healthcare professional."
    ],
    "gp_guidance": "A general physician can review the report.",
    "advanced_care": None,
    "disclaimer": "Educational information, not a diagnosis.",
}


def test_valid_response():
    result = validate_medical_analysis(deepcopy(VALID_ANALYSIS))
    assert result["status"] == "success"


def test_missing_field():
    invalid = deepcopy(VALID_ANALYSIS)
    del invalid["summary"]

    with pytest.raises(ValueError, match="summary"):
        validate_medical_analysis(invalid)


def test_invalid_finding():
    invalid = deepcopy(VALID_ANALYSIS)
    invalid["findings"] = ["Invalid finding"]

    with pytest.raises(ValueError, match="dictionary"):
        validate_medical_analysis(invalid)