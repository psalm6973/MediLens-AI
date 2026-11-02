
def mock_medical_analysis_agent(parsed_report: dict) -> dict:
    """
    Safe fallback that explains extracted report information,
    identifies uncertainty and provides general precautions.
    It does not diagnose or interpret medical conditions.
    """

    if not isinstance(parsed_report, dict):
        raise ValueError("Parsed report must be a dictionary.")

    results = parsed_report.get("results", [])

    if not isinstance(results, list):
        raise ValueError("Parsed report results must be a list.")

    findings = []
    flagged_count = 0
    review_count = 0

    for result in results:
        if not isinstance(result, dict):
            continue

        test_name = str(result.get("test_name") or "Unknown test")
        value = result.get("value")
        unit = str(result.get("unit") or "")
        raw_value = result.get("raw_ocr_value")
        raw_unit = result.get("raw_ocr_unit")
        reference_range = result.get("reference_range")
        flag = result.get("flag")
        reference_status = result.get("reference_status")
        original_line = str(result.get("original_line") or "")

        reported_value = (
            "Value not extracted"
            if value is None
            else f"{value} {unit}".strip()
        )

        alternate_results = []

        for alternate in result.get("alternate_values", []):
            if not isinstance(alternate, dict):
                continue

            alternate_results.append({
                "reported_value": str(alternate.get("value", "Unknown")),
                "raw_ocr_value": alternate.get("raw_ocr_value"),
                "raw_ocr_unit": alternate.get("raw_ocr_unit"),
                "normalized_unit": alternate.get("unit"),
                "reference_range": alternate.get("reference_range"),
                "reference_status": alternate.get("reference_status"),
                "flag": alternate.get("flag"),
                "unit_correction_applied": bool(
                    alternate.get("unit_correction_applied", False)
                ),
                "verification_required": True
            })

        needs_review = (
            result.get("needs_review", True)
            or value is None
            or bool(alternate_results)
            or bool(result.get("correction_applied", False))
            or bool(result.get("unit_correction_applied", False))
        )

        if needs_review:
            review_count += 1

        if flag:
            flagged_count += 1

        if alternate_results:
            observation = (
                "More than one measurement was extracted for this test. "
                "The values must be compared with the original report "
                "before deciding which measurement is correct."
            )
        elif value is None:
            observation = (
                "The system could not reliably extract a result. "
                "The original report needs to be checked."
            )
        elif flag:
            observation = (
                f"The extracted report contains the flag '{flag}'. "
                "This is a reported label, not a confirmed medical finding. "
                "Check the printed reference range and verify the value."
            )
        elif reference_range:
            observation = (
                f"The extracted report lists the reference range "
                f"'{reference_range}'. Compare the reported value with "
                "the original printed range. This fallback cannot confirm "
                "whether the result has clinical significance."
            )
        else:
            observation = (
                "A value was extracted, but a reliable reference range "
                "was not available. Its significance cannot be established "
                "by this fallback."
            )

        findings.append({
            "test_name": test_name,
            "reported_value": reported_value,
            "raw_ocr_value": raw_value,
            "unit": unit,
            "raw_ocr_unit": raw_unit,
            "reference_range": reference_range,
            "reference_status": reference_status,
            "flag": flag,
            "alternate_results": alternate_results,
            "meaning": (
                f"This test is identified as '{test_name}'. "
                "The fallback can organize its extracted information, "
                "but cannot establish a medical interpretation."
            ),
            "observation": observation,
            "verification_required": True,
            "source": (
                "Extracted report data; not independently verified. "
                f"Original text: {original_line[:200]}"
            )
        })

    if findings:
        summary = (
            f"The report contains {len(findings)} extracted test result(s). "
            f"{flagged_count} result(s) contain an extracted report flag, "
            f"and {review_count} result(s) require additional verification. "
            "These counts describe the extracted data only; they do not "
            "indicate how many medical abnormalities are present."
        )
    else:
        summary = (
            "No usable test results were extracted. The original report "
            "needs manual review."
        )

    return {
        "status": "needs_review",
        "analysis_mode": "mock_fallback",
        "summary": summary,
        "findings": findings,
        "general_guidance": [
            "Compare every extracted value and unit with the original report.",
            "Check the printed reference range and any laboratory flags.",
            "Resolve conflicting or alternate OCR measurements before relying on them.",
            "Do not change medication or make treatment decisions based on this output.",
            "Discuss the report with a qualified healthcare professional.",
            "Seek timely medical attention if you have concerning symptoms."
        ],
        "gp_guidance": (
            "Contact a general physician to review the original report, "
            "confirm uncertain measurements and explain their significance "
            "in the context of your health."
        ),
        "advanced_care": None,
        "disclaimer": (
            "MOCK FALLBACK OUTPUT: Gemini was unavailable. This output "
            "organizes extracted report information and identifies "
            "uncertainties. It is not a medical diagnosis, clinical "
            "interpretation or treatment recommendation."
        )
    }
