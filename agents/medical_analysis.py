
import json
import os
import re
from dotenv import load_dotenv
from groq import Groq

from utils.rag_helper import retrieve_documents
from utils.mock_analysis import mock_medical_analysis_agent


load_dotenv()


# ============================================================
# 1. GROQ CLIENT
# ============================================================

def get_groq_client():
    """Create a Groq client using the API key in .env."""

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY was not found. Check your .env file."
        )

    return Groq(api_key=api_key)


# ============================================================
# 2. BUILD MEDICAL CONTEXT USING RAG
# ============================================================

def build_medical_context(results: list[dict]) -> str:
    """Build report context while preserving OCR uncertainty."""

    context_sections = []

    for item in results:

        test_name = item.get("test_name", "Unknown test")

        query = (
            f"{test_name}: purpose, meaning, and general "
            "medical interpretation"
        )

        try:
            retrieved = retrieve_documents(query, top_k=2)
        except Exception:
            retrieved = []

        references = []

        for result in retrieved:

            metadata = result.get("metadata") or {}

            references.append({
                "source": metadata.get("source"),
                "content": result.get("document", "")[:500]
            })

        alternate_values = []

        for alternate in item.get("alternate_values", []):

            if not isinstance(alternate, dict):
                continue

            alternate_values.append({
                "value": alternate.get("value"),
                "raw_ocr_value": alternate.get("raw_ocr_value"),
                "value_candidates": alternate.get("value_candidates", []),
                "value_ambiguous": alternate.get("value_ambiguous", False),

                "unit": alternate.get("unit"),
                "raw_ocr_unit": alternate.get("raw_ocr_unit"),

                "reference_range": alternate.get("reference_range"),
                "reference_status": alternate.get("reference_status"),
                "flag": alternate.get("flag"),

                "needs_review": alternate.get("needs_review", True),
                "needs_review_reasons": alternate.get(
                    "needs_review_reasons", []
                ),

                "original_line": alternate.get("original_line", "")
            })

        context_sections.append({

            "test_name": test_name,

            "primary_result": {
                "value": item.get("value"),
                "raw_ocr_value": item.get("raw_ocr_value"),
                "value_candidates": item.get("value_candidates", []),
                "value_ambiguous": item.get("value_ambiguous", False),

                "unit": item.get("unit"),
                "raw_ocr_unit": item.get("raw_ocr_unit"),

                "reference_range": item.get("reference_range"),
                "reference_status": item.get("reference_status"),
                "flag": item.get("flag"),

                "needs_review": item.get("needs_review", True),
                "needs_review_reasons": item.get(
                    "needs_review_reasons", []
                )
            },

            "alternate_results": alternate_values,

            "needs_review": item.get("needs_review", True),
            "needs_review_reasons": item.get(
                "needs_review_reasons", []
            ),

            "correction_applied": item.get("correction_applied", False),
            "original_line": item.get("original_line", ""),

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

    if not all(
        isinstance(item, str)
        for item in analysis["general_guidance"]
    ):
        raise ValueError("General guidance items must be strings.")

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

            if not isinstance(analysis["advanced_care"][field], str):
                raise ValueError(
                    f"Advanced care '{field}' must be a string."
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
    """Activate deterministic fallback if Groq fails."""

    print("\n--- MOCK FALLBACK ACTIVATED ---", flush=True)
    print("Reason:", reason, flush=True)
    print("--------------------------------\n", flush=True)

    analysis = mock_medical_analysis_agent(parsed_report)

    analysis["analysis_mode"] = "mock_fallback"
    analysis["fallback_reason"] = reason

    return validate_medical_analysis(analysis)


# ============================================================
# 5. ENFORCE OCR VERIFICATION
# ============================================================

def normalize_match_name(name: str) -> str:
    """Normalize names for matching findings to parsed results."""

    name = str(name or "").lower().strip()
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"[^a-z0-9 ]", "", name)

    return name


def enforce_verification(
    analysis: dict,
    results: list[dict]
) -> dict:
    """
    Parser uncertainty is authoritative.

    The LLM cannot remove a verification requirement
    created by the parser.
    """

    result_lookup = {}

    for item in results:

        key = normalize_match_name(item.get("test_name", ""))

        if key:
            result_lookup[key] = item

    for finding in analysis.get("findings", []):

        test_name = normalize_match_name(
            finding.get("test_name", "")
        )

        original = result_lookup.get(test_name)

        if original is None:

            finding["verification_required"] = True
            finding["source"] = None

            finding["observation"] = (
                str(finding.get("observation", ""))
                + " The extracted finding could not be matched "
                  "to a parsed report result and must be verified."
            )

            continue

        primary = original

        needs_review = (
            primary.get("needs_review", True)
            or primary.get("value_ambiguous", False)
            or bool(primary.get("needs_review_reasons", []))
        )

        for alternate in primary.get("alternate_values", []):

            if (
                alternate.get("needs_review", True)
                or alternate.get("value_ambiguous", False)
                or bool(alternate.get("needs_review_reasons", []))
            ):
                needs_review = True

        # The parser controls this field.
        finding["verification_required"] = bool(needs_review)

        # Do not attribute unrelated RAG documents
        # as evidence for individual findings.
        finding["source"] = None

        if needs_review:

            observation = str(
                finding.get("observation", "")
            )

            verification_sentence = (
                " The extracted result requires verification "
                "against the original laboratory report."
            )

            if verification_sentence.strip() not in observation:
                finding["observation"] = (
                    observation + verification_sentence
                )

    report_needs_review = any(

        item.get("needs_review", True)
        or item.get("value_ambiguous", False)
        or bool(item.get("needs_review_reasons", []))

        or any(
            alternate.get("needs_review", True)
            or alternate.get("value_ambiguous", False)
            or bool(alternate.get("needs_review_reasons", []))

            for alternate in item.get("alternate_values", [])
        )

        for item in results
    )

    if report_needs_review:
        analysis["status"] = "needs_review"

    return analysis


# ============================================================
# 6. MEDICAL ANALYSIS AGENT
# ============================================================

def medical_analysis_agent(parsed_report: dict) -> dict:
    """
    Agent 2 workflow:

        1. Receive parsed report.
        2. Retrieve medical knowledge using RAG.
        3. Send report context to Groq GPT-OSS-120B.
        4. Validate the response.
        5. Enforce parser verification requirements.
        6. Use mock fallback if Groq fails.
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
    # GROQ ANALYSIS
    # --------------------------------------------------------

    try:

        medical_context = build_medical_context(results)

        prompt = f"""
You are the medical report explanation component of MediLens-AI.

Your job is to explain extracted medical report information
in simple, understandable language.

IMPORTANT RULES:

1. This is an educational report explanation tool,
   NOT a diagnostic system.

2. Never diagnose a disease or prescribe medication.

3. Treat every extracted result as an unverified OCR candidate.

4. Preserve primary values, raw OCR values, normalized units
   and original OCR units.

5. Treat primary and alternate values as separate OCR candidates.

6. Never assume that the first number on a line is correct.

7. If multiple possible values exist, explain the ambiguity
   and require verification.

8. Never silently correct numeric OCR values.

9. If primary and alternate values differ, preserve both.
   Do not assume they are errors merely because the numbers differ;
   their units may be different.

10. A normalized unit is a controlled OCR correction,
    not proof that the original unit was read correctly.

11. If needs_review is true, clearly mention that the value
    requires verification against the original report.

12. Prefer the reference range printed in the report.

13. Do not assume a value is abnormal based only on
    a general reference document.

14. Use retrieved references only when relevant.
    Do not invent facts or citations.

15. If information is insufficient, clearly say so.

16. Recommend general physician review when appropriate.

17. Add an Advanced Care department only when the available
    report evidence strongly supports further evaluation.
    Never recommend individual doctors.

18. Do not provide treatment instructions or medication doses.

19. Do not treat OCR flags or reference-status labels as
    confirmed clinical interpretations.

20. If OCR verification is required, do not present the
    finding as a confirmed abnormality.

21. Do not infer a patient's age, sex, medical history
    or other missing information.

22. Explain uncertainty rather than guessing.

EXTRACTED REPORT INFORMATION AND RETRIEVED REFERENCES:

{medical_context}

Return ONLY valid JSON using this exact structure:

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
            "source": null
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

        print("\n--- GROQ REQUEST DEBUG ---", flush=True)
        print("Model: openai/gpt-oss-120b", flush=True)
        print("Prompt length:", len(prompt), flush=True)
        print("Report results:", len(results), flush=True)
        print(
            "Retrieved context length:",
            len(medical_context),
            flush=True
        )
        print("--------------------------\n", flush=True)

        client = get_groq_client()

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=3000,
            response_format={
                "type": "json_object"
            }
        )

        if not response.choices:
            raise ValueError("Groq returned no response choices.")

        response_text = response.choices[0].message.content

        if not response_text:
            raise ValueError("Groq returned an empty response.")

        analysis = json.loads(response_text)

        if not isinstance(analysis, dict):
            raise ValueError(
                "Groq returned an unexpected response format."
            )

        analysis = validate_medical_analysis(analysis)

        analysis = enforce_verification(analysis, results)

        analysis = validate_medical_analysis(analysis)

        analysis["analysis_mode"] = "groq"

        print(
            "Groq analysis completed and passed validation.",
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
