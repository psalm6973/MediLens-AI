
from pathlib import Path
from typing import Any
import re


UNIT_PATTERN = (
    r"g/dL|mg/dL|g/L|mg/L|mmol/L|mmol/mol|"
    r"umol/L|µmol/L|mIU/L|mIU/mL|IU/L|U/L|"
    r"ng/mL|pg/mL|cells/µL|cells/uL|/µL|/uL|%"
    r"|RATIO"
)
UNIT_RE = re.compile(UNIT_PATTERN, re.IGNORECASE)


VALUE_RE = re.compile(
    r"^(?P<comparator><=|>=|<|>|≤|≥)?\s*"
    r"(?P<number>-?\d[\d,]*(?:\.\d+)?)$"
)


RANGE_RE = re.compile(
    r"(?P<low>-?\d[\d,]*(?:\.\d+)?)"
    r"\s*(?:-|–|—|to)\s*"
    r"(?P<high>-?\d[\d,]*(?:\.\d+)?)",
    re.IGNORECASE,
)


# Supports symbols and OCR wording such as "< or = 0.30"
LIMIT_RE = re.compile(
    r"(?P<comparator><\s*or\s*=|>\s*or\s*=|<=|>=|<|>|≤|≥)"
    r"\s*(?P<value>\d[\d,]*(?:\.\d+)?)",
    re.IGNORECASE,
)


METADATA_START_RE = re.compile(
    r"^(DRAWN|RECEIVED|REPORTED|PAGE|TEL|FAX|CIN|"
    r"CLIENT CODE|CLIENT'S NAME|PATIENT NAME|PATIENT ID|"
    r"ACCESSION NO|REFERRING CLIENT|DATE OF BIRTH)\b",
    re.IGNORECASE,
)


def to_number(value: str) -> float:
    return float(value.replace(",", "").strip())


def normalize_comparator(comparator: str) -> str:
    comparator = comparator.lower().replace(" ", "")

    if comparator in ("<or=", "≤"):
        return "<="
    if comparator in (">or=", "≥"):
        return ">="

    return comparator


def parse_reference_range(text: str | None) -> dict[str, Any] | None:
    if not text:
        return None

    range_match = RANGE_RE.search(text)

    if range_match:
        try:
            low = to_number(range_match.group("low"))
            high = to_number(range_match.group("high"))
        except ValueError:
            return None

        if low <= high:
            return {
                "type": "range",
                "low": low,
                "high": high,
            }

        return None

    limit_match = LIMIT_RE.search(text)

    if limit_match:
        try:
            value = to_number(limit_match.group("value"))
        except ValueError:
            return None

        return {
            "type": "limit",
            "comparator": normalize_comparator(
                limit_match.group("comparator")
            ),
            "value": value,
        }

    return None


def check_reference_status(
    value: float,
    reference_range: dict[str, Any] | None,
) -> str:
    """Compare a value with its extracted reference interval."""

    if not reference_range:
        return "unknown"

    if reference_range["type"] == "range":
        if value < reference_range["low"]:
            return "below"
        if value > reference_range["high"]:
            return "above"
        return "within"

    if reference_range["type"] == "limit":
        comparator = reference_range["comparator"]
        limit = reference_range["value"]

        if comparator == "<":
            return "above" if value >= limit else "within"
        if comparator == "<=":
            return "above" if value > limit else "within"
        if comparator == ">":
            return "below" if value <= limit else "within"
        if comparator == ">=":
            return "below" if value < limit else "within"

    return "unknown"


def is_suspicious_test_name(test_name: str) -> bool:
    """Reject obvious short OCR fragments without rejecting common abbreviations."""

    words = test_name.split()

    if not words:
        return True

    # Reject fragments like "H e", but retain names like "WBC" or "TSH".
    if len(words) > 1 and all(len(word) <= 2 for word in words):
        return True

    return False


def parse_result_line(line: str) -> dict[str, Any] | None:
    line = line.strip()

    if not line:
        return None

    if METADATA_START_RE.search(line):
        return None

    match = re.match(
        r"^(?P<test_name>[A-Za-z][A-Za-z0-9 /(),.%_-]*?)"
        r"\s*:?\s+"
        r"(?P<value>(?:<=|>=|<|>|≤|≥)?\s*"
        r"-?\d[\d,]*(?:\.\d+)?)"
        r"(?P<remainder>.*)$",
        line,
    )

    if not match:
        return None

    test_name = match.group("test_name").strip(" :-\t")
    raw_value = match.group("value").strip()
    remainder = match.group("remainder").strip()

    if len(test_name) < 3 or is_suspicious_test_name(test_name):
        return None

    value_match = VALUE_RE.match(raw_value)

    if not value_match:
        return None

    try:
        value = to_number(value_match.group("number"))
    except ValueError:
        return None

    comparator = value_match.group("comparator")

    if comparator:
        comparator = normalize_comparator(comparator)

    flag_match = re.search(
        r"\b(High|Low|Abnormal|Critical)\b",
        remainder,
        re.IGNORECASE,
    )
    flag = flag_match.group(1).lower() if flag_match else None

    reference_range = parse_reference_range(remainder)

    remainder_for_unit = RANGE_RE.sub("", remainder)
    remainder_for_unit = LIMIT_RE.sub("", remainder_for_unit)
    remainder_for_unit = re.sub(
        r"\b(High|Low|Abnormal|Critical)\b",
        "",
        remainder_for_unit,
        flags=re.IGNORECASE,
    )

    unit_match = UNIT_RE.search(remainder_for_unit)
    unit = unit_match.group(0) if unit_match else None

    reference_status = check_reference_status(
        value,
        reference_range,
    )

    return {
        "test_name": test_name,
        "value": value,
        "comparator": comparator,
        "unit": unit,
        "reference_range": reference_range,
        "flag": flag,
        "reference_status": reference_status,
        "needs_review": True,
        "original_line": line,
    }


def parse_report_text(text: str) -> dict[str, Any]:
    if not isinstance(text, str):
        raise TypeError("Report text must be a string.")

    if not text.strip():
        raise ValueError("Report text is empty.")

    results = []
    unparsed_lines = []
    unassigned_values = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # Preserve standalone numbers without guessing their test names.
        standalone_match = re.fullmatch(
            r"[-+]?\d[\d,]*(?:\.\d+)?",
            line,
        )

        if standalone_match:
            unassigned_values.append({
                "value": to_number(line),
                "original_line": line,
                "needs_review": True,
            })
            continue

        result = parse_result_line(line)

        if result is not None:
            results.append(result)
        else:
            unparsed_lines.append(line)

    return {
        "results": results,
        "unassigned_values": unassigned_values,
        "unparsed_lines": unparsed_lines,
        "result_count": len(results),
        "unassigned_value_count": len(unassigned_values),
        "parser_version": "0.7",
        "disclaimer": (
            "Extracted values are unverified candidates. Verify "
            "test names, values, units, flags and reference ranges "
            "against the original report. Reference comparisons "
            "are not diagnoses. This parser does not provide "
            "medical advice."
        ),
    }


def parse_report_file(file_path: str) -> dict[str, Any]:
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Report text file not found: {path}"
        )

    text = path.read_text(encoding="utf-8")
    return parse_report_text(text)
