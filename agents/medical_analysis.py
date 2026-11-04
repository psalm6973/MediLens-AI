
import time
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
        except Exception as error:
            print(
                f"RAG retrieval failed for {test_name}: {error}",
                flush=True
            )
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
                "value_candidates": alternate.get(
                    "value_candidates", []
                ),
                "value_ambiguous": alternate.get(
                    "value_ambiguous", False
                ),
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
                "value_candidates": item.get(
                    "value_candidates", []
                ),
                "value_ambiguous": item.get(
                    "value_ambiguous", False
                ),
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

            "correction_applied": item.get(
                "correction_applied", False
            ),
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
# 5. NAME NORMALIZATION
# ============================================================

def normalize_match_name(name: str) -> str:
    """Normalize names for matching findings to parsed results."""

    name = str(name or "").lower().strip()
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"[^a-z0-9 ]", "", name)

    return name


# ============================================================
# 6. ENFORCE VERIFICATION
# ============================================================

def enforce_verification(
    analysis: dict,
    results: list[dict],
    document_metadata: dict | None = None
) -> dict:
    """Preserve extraction uncertainty and original values."""

    document_metadata = document_metadata or {}

    result_lookup = {}

    for item in results:

        key = normalize_match_name(item.get("test_name", ""))

        if key:
            result_lookup[key] = item

    parser_needs_review = False
    unmatched_findings = False

    for item in results:

        if (
            item.get("needs_review", True)
            or item.get("value_ambiguous", False)
            or bool(item.get("needs_review_reasons", []))
        ):
            parser_needs_review = True

        for alternate in item.get("alternate_values", []):

            if not isinstance(alternate, dict):
                continue

            if (
                alternate.get("needs_review", True)
                or alternate.get("value_ambiguous", False)
                or bool(alternate.get("needs_review_reasons", []))
            ):
                parser_needs_review = True

    for finding in analysis.get("findings", []):

        test_name = normalize_match_name(
            finding.get("test_name", "")
        )

        original = result_lookup.get(test_name)

        finding["verification_required"] = True
        finding["source"] = None

        if original is None:

            unmatched_findings = True

            observation = str(finding.get("observation", ""))

            finding["observation"] = (
                observation
                + " This finding could not be matched to an "
                  "extracted report result and requires verification."
            )

            continue

        original_value = original.get("value")
        original_unit = original.get("unit")

        finding["reported_value"] = (
            f"{original_value} {original_unit}".strip()
            if original_unit
            else f"{original_value} (unit missing)"
        )

        needs_review = (
            original.get("needs_review", True)
            or original.get("value_ambiguous", False)
            or bool(original.get("needs_review_reasons", []))
        )

        if needs_review:

            observation = str(finding.get("observation", ""))

            warning = (
                " The extracted result has OCR or parsing uncertainty "
                "and must be checked against the original laboratory report."
            )

            if warning.strip() not in observation:
                finding["observation"] = observation + warning

    extraction_needs_review = bool(
        document_metadata.get("review_required", False)
    )

    if (
        extraction_needs_review
        or parser_needs_review
        or unmatched_findings
    ):
        analysis["status"] = "needs_review"

    analysis["extraction_review_required"] = (
        extraction_needs_review or parser_needs_review
    )

    analysis["original_report_verification_required"] = True

    analysis["extraction_warnings"] = document_metadata.get(
        "extraction_warnings", []
    )

    if extraction_needs_review or parser_needs_review:
        analysis["advanced_care"] = None

    return analysis


# ============================================================
# 7. ALIGN OUTPUT WITH RESULT.HTML
# ============================================================

def prepare_display_fields(
    analysis: dict,
    results: list[dict]
) -> dict:
    """
    Add display fields expected by result.html.

    Apply conservative descriptions to known test labels.
    Do not invent the meaning of unrecognized test names.
    """

    result_lookup = {
        normalize_match_name(item.get("test_name", "")): item
        for item in results
    }

    for finding in analysis.get("findings", []):

        test_name = normalize_match_name(
            finding.get("test_name", "")
        )

        original = result_lookup.get(test_name, {})
        reference_range = original.get("reference_range")

        # Match the template's expected description field.
        finding["what_it_measures"] = finding.get(
            "meaning",
            "The purpose of this test could not be confidently identified."
        )

        # APTT: known test description.
        if test_name == "aptt":

            finding["what_it_measures"] = (
                "Activated partial thromboplastin time (APTT) is a "
                "laboratory test that measures how long blood takes "
                "to clot through part of the coagulation pathway."
            )

        # MNAPTT: retain the label without inventing an expansion.
        elif test_name == "mnaptt":

            finding["what_it_measures"] = (
                "The exact meaning of the laboratory label MNAPTT "
                "could not be confidently established. Its full "
                "meaning should be confirmed with the laboratory "
                "or a healthcare professional."
            )

            finding["observation"] = (
                "The extracted value is "
                f"{finding.get('reported_value', 'not available')}. "
                "The report information available to the system "
                "does not include a reference range for this label. "
                "Its significance therefore cannot be determined "
                "reliably from the extracted information alone."
            )

            finding["verification_required"] = True

        # Missing reference range: do not claim normal or abnormal.
        if not reference_range:

            finding["reference_information_available"] = False

            if test_name != "mnaptt":

                finding["observation"] = (
                    str(finding.get("observation", ""))
                    + " No reference range was available in the "
                      "extracted information, so a range-based "
                      "interpretation cannot be made."
                )

        else:
            finding["reference_information_available"] = True

    # Template expects overall_interpretation.
    if not analysis.get("overall_interpretation"):

        if any(
            normalize_match_name(item.get("test_name", "")) == "mnaptt"
            for item in results
        ):
            analysis["overall_interpretation"] = (
                "The report contains APTT and MNAPTT results. "
                "The extracted APTT value can be compared with "
                "its printed reference range. The MNAPTT label "
                "and its missing reference information require "
                "clarification before its significance can be assessed."
            )
        else:
            analysis["overall_interpretation"] = analysis.get(
                "summary",
                "The extracted findings should be interpreted "
                "alongside the complete laboratory report."
            )

    # Template expects general_physician_guidance.
    analysis["general_physician_guidance"] = analysis.get(
        "general_physician_guidance",
        analysis.get(
            "gp_guidance",
            "A general physician can review the complete report, "
            "confirm the extracted information and decide whether "
            "further evaluation is needed."
        )
    )

    # Keep both names for compatibility with existing code.
    analysis["gp_guidance"] = analysis["general_physician_guidance"]

    return analysis


# ============================================================
# 8. MEDICAL ANALYSIS AGENT
# ============================================================

def medical_analysis_agent(
    parsed_report: dict,
    document_metadata: dict | None = None
) -> dict:
    """
    Agent 2 workflow:

        1. Receive parsed report.
        2. Receive Document Reader metadata.
        3. Retrieve medical knowledge using RAG.
        4. Send context to Groq.
        5. Validate the response.
        6. Enforce original-report verification.
        7. Align output with result.html.
        8. Use mock fallback if Groq fails.
    """

    total_start = time.perf_counter()

    if not isinstance(parsed_report, dict):
        raise ValueError("Parsed report must be a dictionary.")

    if document_metadata is None:
        document_metadata = {}

    if not isinstance(document_metadata, dict):
        raise ValueError("Document metadata must be a dictionary.")

    results = parsed_report.get("results", [])

    if not isinstance(results, list):
        raise ValueError("Parsed report results must be a list.")

    # --------------------------------------------------------
    # HANDLE EMPTY REPORTS
    # --------------------------------------------------------

    if not results:

        analysis = use_mock_fallback(
            parsed_report,
            "No usable report results were extracted."
        )

        analysis = enforce_verification(
            analysis,
            results,
            document_metadata
        )

        analysis = prepare_display_fields(analysis, results)

        print(
            f"Total medical analysis time: "
            f"{time.perf_counter() - total_start:.2f}s",
            flush=True
        )

        return analysis

    # --------------------------------------------------------
    # GROQ ANALYSIS
    # --------------------------------------------------------

    try:

        rag_start = time.perf_counter()

        medical_context = build_medical_context(results)

        print(
            f"RAG context time: "
            f"{time.perf_counter() - rag_start:.2f}s",
            flush=True
        )

        extraction_context = {
            "extraction_method": document_metadata.get(
                "extraction_method"
            ),
            "quality_status": document_metadata.get(
                "quality_status"
            ),
            "review_required": document_metadata.get(
                "review_required", True
            ),
            "extraction_warnings": document_metadata.get(
                "extraction_warnings", []
            )
        }

        prompt = f"""
You are the medical report explanation component of MediLens-AI.

Explain extracted medical report information in simple language.
This is an educational tool, NOT a diagnostic system.

IMPORTANT RULES:

1. Never diagnose a disease or prescribe medication.
2. Treat extracted values as unverified until checked.
3. Preserve the exact extracted values and units.
4. Never silently correct OCR values or decimal placement.
5. Do not invent missing values or reference ranges.
6. Prefer reference ranges printed in the report.
7. Do not assume a result is abnormal using an unrelated range.
8. Explain uncertainty clearly.
9. Do not invent test-name expansions.
10. If a test label is unclear, preserve its original name.
11. Do not confidently explain an unrecognized test.
12. Every finding must require verification against the original report.
13. Do not treat RAG references as proof of extracted values.
14. Recommend general physician review when appropriate.
15. Add an Advanced Care department only when strongly supported.
16. Never recommend individual doctors.
17. Do not provide medication doses or treatment instructions.
18. Do not infer missing patient details.
19. Do not describe extracted values as clinically confirmed.
20. Keep explanations concise, specific and non-repetitive.

SPECIFIC TEST-NAME SAFEGUARDS:

- APTT is Activated Partial Thromboplastin Time. It is a blood
  coagulation test. Explain this only when the extracted label
  is exactly APTT.

- MNAPTT must remain MNAPTT. Do not expand this abbreviation,
  assume it is a variation of APTT, or invent its laboratory
  meaning. If its meaning is not established by reliable context,
  state that clarification is needed.

- A missing reference range means the result cannot be reliably
  classified using a range. Do not call it normal or abnormal.

DOCUMENT EXTRACTION INFORMATION:

{json.dumps(extraction_context, indent=2, default=str)}

EXTRACTED REPORT INFORMATION AND RETRIEVED REFERENCES:

{medical_context}

Return ONLY valid JSON using this structure:

{{
    "status": "success",
    "summary": "A concise, report-specific overview.",
    "overall_interpretation": "A concise explanation of what the available findings collectively show and what remains uncertain.",
    "findings": [
        {{
            "test_name": "Original extracted test name",
            "reported_value": "Extracted value and unit",
            "meaning": "What the test measures, if reliably known.",
            "observation": "Careful interpretation using the available reference information.",
            "verification_required": true,
            "source": null
        }}
    ],
    "general_guidance": [
        "Relevant, safe and concise guidance."
    ],
    "gp_guidance": "Useful general physician guidance.",
    "general_physician_guidance": "Useful general physician guidance.",
    "advanced_care": null,
    "disclaimer": "This is educational information, not a diagnosis."
}}

If a specialist department is not strongly supported,
advanced_care must be null.

Do not repeat the same warning in multiple sections.
Do not invent missing reference ranges or test meanings.
"""

        print("\n--- GROQ REQUEST DEBUG ---", flush=True)
        print("Model: openai/gpt-oss-120b", flush=True)
        print("Prompt length:", len(prompt), flush=True)
        print("Report results:", len(results), flush=True)
        print(
            "Extraction review required:",
            extraction_context["review_required"],
            flush=True
        )
        print("--------------------------\n", flush=True)

        client = get_groq_client()

        groq_start = time.perf_counter()

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

        print(
            f"Groq response time: "
            f"{time.perf_counter() - groq_start:.2f}s",
            flush=True
        )

        if not response.choices:
            raise ValueError("Groq returned no response choices.")

        response_text = response.choices[0].message.content

        if not response_text:
            raise ValueError("Groq returned an empty response.")

        analysis = json.loads(response_text)

        analysis = validate_medical_analysis(analysis)

        analysis = enforce_verification(
            analysis,
            results,
            document_metadata
        )

        analysis = prepare_display_fields(analysis, results)

        analysis = validate_medical_analysis(analysis)

        analysis["analysis_mode"] = "groq"

        print(
            "Groq analysis completed and passed validation.",
            flush=True
        )

        print(
            f"Total medical analysis time: "
            f"{time.perf_counter() - total_start:.2f}s",
            flush=True
        )

        return analysis

    except Exception as error:

        fallback_reason = (
            f"{type(error).__name__}: {str(error)}"
        )

        analysis = use_mock_fallback(
            parsed_report,
            fallback_reason
        )

        analysis = enforce_verification(
            analysis,
            results,
            document_metadata
        )

        analysis = prepare_display_fields(analysis, results)

        print(
            f"Total medical analysis time: "
            f"{time.perf_counter() - total_start:.2f}s",
            flush=True
        )

        return analysis
