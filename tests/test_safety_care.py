
from agents.safety_care import safety_care_agent


safe_analysis = {
    "status": "success",
    "summary": "The report contains laboratory test results for review.",
    "findings": [
        {
            "test_name": "Sample Test",
            "reported_value": "10",
            "meaning": "This result should be interpreted in clinical context.",
            "observation": "No conclusion can be made from this value alone.",
            "verification_required": False,
            "source": "Sample medical reference"
        }
    ],
    "general_guidance": [
        "Maintain a balanced diet.",
        "Discuss the report with a healthcare professional."
    ],
    "gp_guidance": "Contact a general physician for further information.",
    "advanced_care": None,
    "disclaimer": "This explanation is educational and is not a diagnosis."
}


unsafe_analysis = {
    "status": "success",
    "summary": "You definitely have a confirmed condition.",
    "findings": [],
    "general_guidance": [
        "Stop taking your prescribed medication."
    ],
    "gp_guidance": "Contact a general physician.",
    "advanced_care": None,
    "disclaimer": "This is a medical diagnosis."
}


def test_safe_analysis():
    result = safety_care_agent(safe_analysis)

    assert result["status"] == "passed_checks"
    assert result["review_required"] is False

    print("PASS: Safe sample passed the safety checks.")


def test_unsafe_analysis():
    result = safety_care_agent(unsafe_analysis)

    assert result["status"] == "needs_review"
    assert result["review_required"] is True
    assert len(result["safety_flags"]) > 0

    print("PASS: Risky sample was flagged for review.")
    print("Detected flags:")

    for flag in result["safety_flags"]:
        print("-", flag)


def test_invalid_input():
    result = safety_care_agent(None)

    assert result["status"] == "needs_review"
    assert result["review_required"] is True

    print("PASS: Invalid input was handled safely.")


if __name__ == "__main__":
    print("\n--- SAFETY CARE AGENT TESTS ---\n")

    test_safe_analysis()
    test_unsafe_analysis()
    test_invalid_input()

    print("\n--- TESTS COMPLETED ---")

