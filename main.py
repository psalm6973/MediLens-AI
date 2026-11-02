
from pathlib import Path

from agents.document_reader import document_reader_agent
from agents.medical_analysis import (
    medical_analysis_agent,
    validate_medical_analysis,
)
from agents.safety_care import safety_care_agent


def run_medilens(file_path: str) -> dict:
    """
    Run the complete MediLens-AI pipeline.

    Agent 1: Read and parse the report.
    Agent 2: Analyse the parsed results.
    Validation: Check Agent 2's output structure.
    Agent 3: Perform safety checks.
    """

    report_path = Path(file_path)

    # --------------------------------------------------
    # AGENT 1: DOCUMENT READER
    # --------------------------------------------------
    if not report_path.is_file():
        return {
            "status": "error",
            "stage": "document_reader",
            "message": f"Report file not found: {file_path}",
        }

    try:
        document_result = document_reader_agent(str(report_path))

        if document_result.get("status") != "success":
            return {
                "status": "needs_review",
                "stage": "document_reader",
                "message": "The report could not be processed successfully.",
                "details": document_result,
            }

        parsed_report = document_result.get("parsed_report", {})

        if not isinstance(parsed_report, dict):
            return {
                "status": "needs_review",
                "stage": "document_reader",
                "message": "The parsed report has an invalid format.",
            }

    except Exception as error:
        return {
            "status": "error",
            "stage": "document_reader",
            "message": "An error occurred while reading the report.",
            "details": str(error),
        }

    # --------------------------------------------------
    # AGENT 2: MEDICAL ANALYSIS
    # --------------------------------------------------
    try:
        medical_analysis = medical_analysis_agent(parsed_report)

        if not isinstance(medical_analysis, dict):
            raise ValueError("Medical analysis must be a dictionary.")

        # Validate the structure even when review is required.
        medical_analysis = validate_medical_analysis(medical_analysis)

        analysis_needs_review = (
            medical_analysis.get("status") != "success"
        )

    except Exception as error:
        return {
            "status": "needs_review",
            "stage": "medical_analysis",
            "message": "Medical analysis failed or did not pass validation.",
            "details": str(error),
        }

    # --------------------------------------------------
    # AGENT 3: SAFETY CARE
    # --------------------------------------------------
    try:
        safety_result = safety_care_agent(medical_analysis)

        if not isinstance(safety_result, dict):
            raise ValueError("Safety check must return a dictionary.")

    except Exception as error:
        return {
            "status": "needs_review",
            "stage": "safety_care",
            "message": "The safety check could not be completed.",
            "details": str(error),
            "analysis": medical_analysis,
        }

    safety_check = {
        "status": safety_result.get("status"),
        "review_required": safety_result.get("review_required", True),
        "safety_flags": safety_result.get("safety_flags", []),
        "message": safety_result.get("message"),
    }

    final_analysis = safety_result.get("analysis", medical_analysis)

    # --------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------

    # Safety concerns take priority.
    if safety_check["review_required"]:
        return {
            "status": "needs_review",
            "stage": "safety_care",
            "message": safety_check["message"],
            "parsed_report": parsed_report,
            "analysis": final_analysis,
            "safety_flags": safety_check["safety_flags"],
            "safety_check": safety_check,
        }

    # Preserve Agent 2's review status even if safety checks pass.
    if analysis_needs_review:
        return {
            "status": "needs_review",
            "stage": "medical_analysis",
            "message": "Medical analysis requires further review. Safety checks completed.",
            "parsed_report": parsed_report,
            "analysis": final_analysis,
            "safety_flags": safety_check["safety_flags"],
            "safety_check": safety_check,
        }

    return {
        "status": "success",
        "message": "The report passed the basic processing and safety checks.",
        "parsed_report": parsed_report,
        "analysis": final_analysis,
        "safety_check": safety_check,
    }


if __name__ == "__main__":
    print("MediLens-AI workflow controller is ready.")
    print("Use run_medilens(file_path) to process a report.")
