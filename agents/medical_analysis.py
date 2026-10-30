
import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from utils.rag_helper import retrieve_documents

load_dotenv()


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY was not found. Check your .env file."
        )

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=180000)
    )


def build_medical_context(results: list[dict]) -> str:
    """Retrieve reference information for each candidate test result."""

    context_sections = []

    for item in results:
        test_name = item.get("test_name", "Unknown test")
        value = item.get("value", "Not available")
        unit = item.get("unit") or ""
        reference_range = item.get("reference_range")
        original_line = item.get("original_line", "")

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
                "content": result.get("document", "")[:1000]
            })

        context_sections.append({
            "test_name": test_name,
            "value": value,
            "unit": unit,
            "reference_range": reference_range,
            "reference_status": item.get("reference_status", "unknown"),
            "flag": item.get("flag"),
            "needs_review": item.get("needs_review", True),
            "original_line": original_line,
            "retrieved_references": references
        })

    return json.dumps(context_sections, indent=2, default=str)


def medical_analysis_agent(parsed_report: dict) -> dict:
    """Explain candidate report findings using retrieved references."""

    results = parsed_report.get("results", [])

    if not results:
        return {
            "status": "needs_review",
            "summary": "No report results could be reliably extracted.",
            "findings": [],
            "general_guidance": [],
            "gp_guidance": (
                "Please have the original report reviewed by a "
                "qualified healthcare professional."
            ),
            "advanced_care": None,
            "disclaimer": (
                "This tool provides educational information, not "
                "a medical diagnosis."
            )
        }

    medical_context = build_medical_context(results)

    prompt = f"""
You are the medical report explanation component of MediLens-AI.

Explain extracted medical report information in simple language.

IMPORTANT RULES:

1. This is an educational report explanation tool, NOT a
   diagnostic system.
2. Never diagnose a disease or prescribe medication.
3. Treat every extracted result as an unverified OCR candidate.
4. Preserve the extracted value, unit and reference range.
   Never silently correct or invent them.
5. If needs_review is true, clearly mention that the value
   requires verification against the original report.
6. Do not assume a value is abnormal based only on a
   general reference document.
7. Prefer the reference range printed in the report.
8. Use retrieved references only when relevant.
   Do not invent facts or citations.
9. If information is insufficient, clearly say so.
10. Recommend general physician review when appropriate.
11. Add an Advanced Care department only when the report
    evidence strongly supports further evaluation.
    Do not recommend individual doctors.
12. Do not provide treatment instructions or medication doses.
13. Do not treat OCR flags or reference-status labels as
    confirmed clinical interpretations.
14. If OCR verification is required, do not present the
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
            "reported_value": "Original extracted value and unit",
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


    client = get_gemini_client()

    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

    except Exception as e:
        raise RuntimeError(
            f"Gemini API request failed: {str(e)}"
        ) from e

    if not response.text:
        raise ValueError("Gemini returned an empty response.")

    try:
        analysis = json.loads(response.text)

    except (json.JSONDecodeError, TypeError):
        raise ValueError(
            "Gemini returned an invalid JSON response. Please try again."
        )

    if not isinstance(analysis, dict):
        raise ValueError("Gemini returned an unexpected response format.")

    return analysis
