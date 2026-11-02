
from agents.medical_analysis import validate_medical_analysis


# A valid sample response from the Medical Analysis Agent
valid_analysis = {
    "status": "success",
    "summary": "The report contains a sample test result.",
    "findings": [
        {
            "test_name": "Sample Test",
            "reported_value": "10",
            "meaning": "A sample explanation.",
            "observation": "The value requires interpretation in context.",
            "verification_required": False,
            "source": "Sample medical reference"
        }
    ],
    "general_guidance": [
        "Discuss the report with a qualified healthcare professional."
    ],
    "gp_guidance": "Contact a general physician for further information.",
    "advanced_care": None,
    "disclaimer": "This is an educational explanation, not a diagnosis."
}


def test_valid_response():
    try:
        result = validate_medical_analysis(valid_analysis)
        print("PASS: Valid response accepted.")
        print("Status:", result["status"])
    except Exception as error:
        print("FAIL: Valid response rejected.")
        print(error)


def test_missing_field():
    invalid_analysis = valid_analysis.copy()
    del invalid_analysis["summary"]

    try:
        validate_medical_analysis(invalid_analysis)
        print("FAIL: Response with a missing field was accepted.")
    except ValueError:
        print("PASS: Missing field correctly rejected.")
    except Exception as error:
        print("Unexpected error:", error)


def test_invalid_finding():
    invalid_analysis = valid_analysis.copy()
    invalid_analysis["findings"] = ["This should be a dictionary"]

    try:
        validate_medical_analysis(invalid_analysis)
        print("FAIL: Invalid finding was accepted.")
    except ValueError:
        print("PASS: Invalid finding correctly rejected.")
    except Exception as error:
        print("Unexpected error:", error)


if __name__ == "__main__":
    print("\n--- MEDICAL ANALYSIS VALIDATION TESTS ---\n")

    test_valid_response()
    test_missing_field()
    test_invalid_finding()

    print("\n--- TESTS COMPLETED ---")
