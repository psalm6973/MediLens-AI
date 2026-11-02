
import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from utils.rag_helper import retrieve_documents
from utils.mock_analysis import mock_medical_analysis_agent


load_dotenv()


# ============================================================
# 1. GEMINI CLIENT
# ============================================================

def get_gemini_client():
    """Create a Gemini client using the API key in .env."""

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY was not found. Check your .env file."
        )

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=180000)
    )


# ============================================================
# 2. BUILD MEDICAL CONTEXT USING RAG
# ============================================================

def build_medical_context(results: list[dict]) -> str:
    """
    Retrieve relevant medical reference information.

    Preserve primary values, alternate values, raw OCR data,
    normalized units and verification information.
    """

    context_sections = []

    for item in results:

        test_name = item.get("test_name", "Unknown test")

        query = (
            f"{test_name}: purpose, meaning, reference range "
            "and factors that may affect this test"
        )

        retrieved = retrieve_documents(query, top_k=1)

        references = []

        for result in retrieved:

            metadata = result.get("metadata") or {}

            references.append({
                "source": metadata.get("source", "Unknown source"),
                "content": result.get("document", "")[:300]
            })

        # Preserve alternate measurement rows.
        alternate_values = []

        for alternate in item.get("alternate_values", []):

            if not isinstance(alternate, dict):
                continue

            alternate_values.append({
                "value": alternate.get("value"),
                "raw_ocr_value": alternate.get("raw_ocr_value"),
                "unit": alternate.get("unit"),
                "raw_ocr_unit": alternate.get("raw_ocr_unit"),
                "unit_correction_applied": alternate.get(
                    "unit_correction_applied", False
                ),
                "reference_range": alternate.get("reference_range"),
                "reference_status": alternate.get("reference_status"),
                "flag": alternate.get("flag"),
                "needs_review": alternate.get("needs_review", True),
                "original_line": alternate.get("original_line", "")
            })

        context_sections.append({

            "test_name": test_name,

            # Primary measurement
            "primary_result": {
                "value": item.get("value"),
                "raw_ocr_value": item.get("raw_ocr_value"),
                "unit": item.get("unit"),
                "raw_ocr_unit": item.get("raw_ocr_unit"),
                "unit_correction_applied": item.get(
                    "unit_correction_applied", False
                ),
                "reference_range": item.get("reference_range"),
                "reference_status": item.get(
                    "reference_status", "unknown"
                ),
                "flag": item.get("flag")
            },

            # Alternate measurements
            "alternate_results": alternate_values,

            # Verification information
            "needs_review": item.get("needs_review", True),
            "correction_applied": item.get(
                "correction_applied", False
            ),
            "original_line": item.get("original_line", ""),

            # RAG references
            "retrieved_references": references
        })

    return json.dumps(context_sections, indent=2, default=str)


# ============================================================
# 3. VALIDATE MEDICAL ANALYSIS OUTPUT
# ============================================================

def validate_medical_analysis(analysis: dict) -> dict:
    """Check that Agent 2 returned the required structure."""

    if not isinstance(analysis, dict):
        raise ValueError("Medical analysis must be a dictionary.")

    required_fields = [
        "status",
        "summary",
        "findings",
        "general_guidance",
        "gp_guidance",
        "advanced_care",
        "disclaimer"
    ]

    missing_fields = [
        field for field in required_fields
        if field not in analysis
    ]

    if missing_fields:
        raise ValueError(
            f"Medical analysis is missing fields: {missing_fields}"
        )

    if analysis["status"] not in ["success", "needs_review"]:
        raise ValueError("Invalid medical analysis status.")

    if not isinstance(analysis["summary"], str):
        raise ValueError("Summary must be a string.")

    if not isinstance(analysis["findings"], list):
        raise ValueError("Findings must be a list.")

    if not isinstance(analysis["general_guidance"], list):
        raise ValueError("General guidance must be a list.")

    if not isinstance(analysis["gp_guidance"], str):
        raise ValueError("GP guidance must be a string.")

    if not isinstance(analysis["disclaimer"], str):
        raise ValueError("Disclaimer must be a string.")

    if analysis["advanced_care"] is not None:

        if not isinstance(analysis["advanced_care"], dict):
            raise ValueError(
                "Advanced care must be a dictionary or None."
            )

        for field in ["department", "reason"]:

            if field not in analysis["advanced_care"]:
                raise ValueError(
                    f"Advanced care is missing the '{field}' field."
                )

    for finding in analysis["findings"]:

        if not isinstance(finding, dict):
            raise ValueError("Each finding must be a dictionary.")

        finding_fields = [
            "test_name",
            "reported_value",
            "meaning",
            "observation",
            "verification_required",
            "source"
        ]

        for field in finding_fields:

            if field not in finding:
                raise ValueError(
                    f"A finding is missing the '{field}' field."
                )

        if not isinstance(finding["verification_required"], bool):
            raise ValueError(
                "verification_required must be True or False."
            )

    return analysis


# ============================================================
# 4. MOCK FALLBACK
# ============================================================

def use_mock_fallback(
    parsed_report: dict,
    reason: str
) -> dict:
    """
    Activate deterministic fallback when Gemini analysis
    is unavailable or its response cannot be validated.
    """

    print("\n--- MOCK FALLBACK ACTIVATED ---", flush=True)
    print("Reason:", reason, flush=True)
    print("--------------------------------\n", flush=True)

    analysis = mock_medical_analysis_agent(parsed_report)

    analysis["analysis_mode"] = "mock_fallback"
    analysis["fallback_reason"] = reason

    return validate_medical_analysis(analysis)


# ============================================================
# 5. MEDICAL ANALYSIS AGENT
# ============================================================

def medical_analysis_agent(parsed_report: dict) -> dict:
    """
    Agent 2 workflow:

        1. Receive parsed report.
        2. Retrieve medical knowledge using RAG.
        3. Send complete report context to Gemini.
        4. Validate Gemini response.
        5. Activate mock fallback if anything fails.
    """

    if not isinstance(parsed_report, dict):
        raise ValueError("Parsed report must be a dictionary.")

    results = parsed_report.get("results", [])

    if not isinstance(results, list):
        raise ValueError("Parsed report results must be a list.")

    # --------------------------------------------------------
    # HANDLE EMPTY REPORTS
    # --------------------------------------------------------

    if not results:

        return use_mock_fallback(
            parsed_report,
            "No usable report results were extracted."
        )

    # --------------------------------------------------------
    # GEMINI ANALYSIS
    # --------------------------------------------------------

    try:

        medical_context = build_medical_context(results)

        prompt = f"""
You are the medical report explanation component of MediLens-AI.

Explain extracted medical report information in simple language.

IMPORTANT RULES:

1. This is an educational report explanation tool, NOT a
   diagnostic system.

2. Never diagnose a disease or prescribe medication.

3. Treat every extracted result as an unverified OCR candidate.

4. Preserve the primary extracted value, raw OCR value,
   normalized unit and original OCR unit.

5. Preserve alternate measurements. Never silently discard,
   combine, average or replace an alternate value.

6. Never silently correct numeric OCR values.

7. If primary and alternate values disagree, clearly explain
   that the extracted information needs manual verification.

8. A normalized unit is a controlled OCR correction, not
   proof that the original unit was read correctly.

9. If needs_review is true, clearly mention that the value
   requires verification against the original report.

10. Do not assume a value is abnormal based only on a
    general reference document.

11. Prefer the reference range printed in the report.

12. Use retrieved references only when relevant.
    Do not invent facts or citations.

13. If information is insufficient, clearly say so.

14. Recommend general physician review when appropriate.

15. Add an Advanced Care department only when report evidence
    strongly supports further evaluation. Do not recommend
    individual doctors.

16. Do not provide treatment instructions or medication doses.

17. Do not treat OCR flags or reference-status labels as
    confirmed clinical interpretations.

18. If OCR verification is required, do not present the
    finding as a confirmed abnormality.

EXTRACTED REPORT INFORMATION AND RETRIEVED REFERENCES:

{medical_context}

Return ONLY valid JSON using this structure:

{{
    "status": "success",
    "summary": "Simple overall explanation of the available report.",
    "findings": [
        {{
            "test_name": "Test name",
            "reported_value": "Primary extracted value and unit",
            "meaning": "General explanation of what this test measures.",
            "observation": "Careful explanation of the available result.",
            "verification_required": true,
            "source": "Retrieved reference filename or unavailable"
        }}
    ],
    "general_guidance": [
        "General, safe guidance relevant to the report."
    ],
    "gp_guidance": "When and why general physician review may be useful.",
    "advanced_care": {{
        "department": "Department name",
        "reason": "Evidence-based reason for further evaluation."
    }},
    "disclaimer": "This is educational information, not a diagnosis."
}}

If no specialist department is clearly supported,
set advanced_care to null.

If information is insufficient, explain the limitation.

Do not invent missing values or reference ranges.
"""

        # Debug information
        print("\n--- GEMINI REQUEST DEBUG ---", flush=True)
        print("Model: gemini-3.8-flash", flush=True)
        print("Prompt length:", len(prompt), flush=True)
        print("Report results:", len(results), flush=True)
        print(
            "Retrieved context length:",
            len(medical_context),
            flush=True
        )
        print("---------------------------\n", flush=True)

        client = get_gemini_client()

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        if not response.text:
            raise ValueError("Gemini returned an empty response.")

        analysis = json.loads(response.text)

        if not isinstance(analysis, dict):
            raise ValueError(
                "Gemini returned an unexpected response format."
            )

        analysis = validate_medical_analysis(analysis)

        analysis["analysis_mode"] = "gemini"

        print(
            "Gemini analysis completed and passed validation.",
            flush=True
        )

        return analysis

    except Exception as error:

        fallback_reason = (
            f"{type(error).__name__}: {str(error)}"
        )

        return use_mock_fallback(
            parsed_report,
            fallback_reason
        )
