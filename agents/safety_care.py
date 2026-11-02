
import re
from copy import deepcopy


# Phrases that may indicate an unsafe or overly certain medical claim.
DIAGNOSIS_PATTERNS = [
    r"\byou have been diagnosed with\b",
    r"\byou are diagnosed with\b",
    r"\byou definitely have\b",
    r"\bthis confirms that you have\b",
    r"\byou have a confirmed case of\b",
]

# Phrases that may indicate medication or treatment instructions.
TREATMENT_PATTERNS = [
    r"\bstop taking\b",
    r"\bstart taking\b",
    r"\bincrease your dose\b",
    r"\bdecrease your dose\b",
    r"\bdouble your dose\b",
    r"\bprescribe(?:d|s)?\b",
    r"\btake\s+\w+\s+\d+\s*mg\b",
]


def collect_analysis_text(analysis: dict) -> str:
    """Collect the generated medical explanation into searchable text."""

    text_parts = [
        str(analysis.get("summary", "")),
        str(analysis.get("gp_guidance", "")),
        str(analysis.get("disclaimer", "")),
    ]

    guidance = analysis.get("general_guidance", [])
    if isinstance(guidance, list):
        text_parts.extend(str(item) for item in guidance)

    findings = analysis.get("findings", [])
    if isinstance(findings, list):
        for finding in findings:
            if isinstance(finding, dict):
                for key in ("meaning", "observation"):
                    text_parts.append(str(finding.get(key, "")))

    advanced_care = analysis.get("advanced_care")
    if isinstance(advanced_care, dict):
        text_parts.append(str(advanced_care.get("reason", "")))

    return " ".join(text_parts)


def safety_care_agent(analysis: dict) -> dict:
    """
    Perform a basic safety check on the Medical Analysis Agent's output.

    This is a rule-based software check, not a clinical review.
    It does not verify whether medical interpretations are correct.
    """

    if not isinstance(analysis, dict):
        return {
            "status": "needs_review",
            "review_required": True,
            "safety_flags": ["The medical analysis output is not a dictionary."],
            "analysis": None,
            "message": "The analysis could not pass the safety checks.",
        }

    checked_analysis = deepcopy(analysis)
    safety_flags = []

    # Check required output fields.
    required_fields = [
        "status",
        "summary",
        "findings",
        "general_guidance",
        "gp_guidance",
        "advanced_care",
        "disclaimer",
    ]

    for field in required_fields:
        if field not in checked_analysis:
            safety_flags.append(f"Missing required field: {field}")

    # Check important field types.
    if not isinstance(checked_analysis.get("summary"), str):
        safety_flags.append("The summary is missing or has an invalid format.")

    if not isinstance(checked_analysis.get("findings"), list):
        safety_flags.append("Findings must be provided as a list.")

    if not isinstance(checked_analysis.get("general_guidance"), list):
        safety_flags.append("General guidance must be provided as a list.")

    if not isinstance(checked_analysis.get("gp_guidance"), str):
        safety_flags.append("GP guidance is missing or has an invalid format.")

    if not isinstance(checked_analysis.get("disclaimer"), str):
        safety_flags.append("The disclaimer is missing or has an invalid format.")

    # Check individual findings.
    findings = checked_analysis.get("findings", [])

    if isinstance(findings, list):
        for index, finding in enumerate(findings):
            if not isinstance(finding, dict):
                safety_flags.append(
                    f"Finding {index + 1} has an invalid format."
                )
                continue

            if not isinstance(finding.get("verification_required"), bool):
                safety_flags.append(
                    f"Finding {index + 1} has an invalid verification status."
                )

    # Check Advanced Care information.
    advanced_care = checked_analysis.get("advanced_care")

    if advanced_care is not None:
        if not isinstance(advanced_care, dict):
            safety_flags.append(
                "Advanced Care must be a dictionary or null."
            )
        elif not advanced_care.get("department") or not advanced_care.get("reason"):
            safety_flags.append(
                "Advanced Care is missing its department or reason."
            )

    # Check for potentially unsafe wording.
    searchable_text = collect_analysis_text(checked_analysis).lower()

    for pattern in DIAGNOSIS_PATTERNS:
        if re.search(pattern, searchable_text):
            safety_flags.append(
                "Potentially definitive diagnosis wording detected."
            )
            break

    for pattern in TREATMENT_PATTERNS:
        if re.search(pattern, searchable_text):
            safety_flags.append(
                "Potential medication or treatment instruction detected."
            )
            break

    # Ensure the response includes a healthcare-professional reminder.
    gp_guidance = checked_analysis.get("gp_guidance", "")

    if isinstance(gp_guidance, str) and not gp_guidance.strip():
        safety_flags.append("GP guidance is empty.")

    # Produce the safety-check result.
    review_required = len(safety_flags) > 0

    if review_required:
        status = "needs_review"
        message = (
            "Potential safety or formatting concerns were detected. "
            "The output should be reviewed before being shown to the user."
        )
    else:
        status = "passed_checks"
        message = (
            "No issues were detected by the basic safety rules. "
            "This does not mean the medical interpretation is clinically verified."
        )

    return {
        "status": status,
        "review_required": review_required,
        "safety_flags": safety_flags,
        "analysis": checked_analysis,
        "message": message,
    }
