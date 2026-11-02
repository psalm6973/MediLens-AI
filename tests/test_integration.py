
import json
from pathlib import Path

from main import run_medilens


# Resolve the project root regardless of the terminal's working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

SAMPLE_REPORT = (
    PROJECT_ROOT
    / "data"
    / "datasets"
    / "ekacare"
    / "images"
    / "report_004.png"
)


def test_complete_workflow():
    print("\n--- MEDILENS-AI INTEGRATION TEST ---\n")

    if not SAMPLE_REPORT.is_file():
        print("FAIL: Sample report was not found.")
        print("Expected location:", SAMPLE_REPORT)
        return

    print("Input report:", SAMPLE_REPORT.name)
    print("\nRunning all three agents...\n")

    result = run_medilens(str(SAMPLE_REPORT))

    print("--- WORKFLOW RESULT ---")
    print("Status:", result.get("status"))
    print("Message:", result.get("message"))

    if result.get("status") == "success":
        print("\nPASS: Complete workflow finished.")

        analysis = result.get("analysis", {})

        print("\n--- MEDICAL ANALYSIS ---")
        print("Summary:")
        print(analysis.get("summary"))

        print("\nFindings:")
        for finding in analysis.get("findings", []):
            print(
                f"- {finding.get('test_name')}: "
                f"{finding.get('reported_value')}"
            )

        print("\nGeneral guidance:")
        for item in analysis.get("general_guidance", []):
            print("-", item)

        print("\nAdvanced Care:")
        print(analysis.get("advanced_care"))

        print("\nSafety check:")
        print(json.dumps(result.get("safety_check"), indent=4))

    elif result.get("status") == "needs_review":
        print("\nREVIEW REQUIRED")
        print("Stage:", result.get("stage"))
        print("Details:", result.get("details"))
        print("Safety flags:", result.get("safety_flags"))

    else:
        print("\nFAIL: Workflow could not complete.")
        print("Stage:", result.get("stage"))
        print("Details:", result.get("details"))


if __name__ == "__main__":
    test_complete_workflow()
