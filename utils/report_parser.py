
from pathlib import Path
from typing import Any
import re


# Common laboratory units
UNIT_RE = re.compile(
    r"g/dL|mg/dL|g/L|mg/L|mmol/L|mmol/mol|"
    r"umol/L|µmol/L|mIU/L|mIU/mL|IU/L|U/L|"
    r"ng/mL|pg/mL|cells/µL|cells/uL|/µL|/uL|%",
    re.IGNORECASE,
)

# Numeric result, optionally with a comparison symbol
VALUE_RE = re.compile(
    r"^(?P<comparator><=|>=|<|>)?\s*"
    r"(?P<number>-?\d[\d,]*(?:\.\d+)?)$"
)

# Two-sided reference interval, for example 6.0 - 8.0
RANGE_RE = re.compile(
    r"(?P<low>-?\d[\d,]*)"
    r"(?:\.(?P<low_decimal>\d+))?"
    r"\s*(?:-|to)\s*"
    r"(?P<high>-?\d[\d,]*)"
    r"(?:\.(?P<high_decimal>\d+))?",
    re.IGNORECASE,
)


def to_number(value: str) -> float:
    """Convert a numeric string to a float."""
    return float(value.replace(",", "").strip())


def parse_reference_range(
    text: str | None,
) -> dict[str, float] | None:
    """Extract a two-sided reference interval."""
    if not text:
        return None

    match = RANGE_RE.search(text)
    if not match:
        return None

    low_text = match.group("low")
    low_decimal = match.group("low_decimal")
    if low_decimal:
        low_text += "." + low_decimal

    high_text = match.group("high")
    high_decimal = match.group("high_decimal")
    if high_decimal:
        high_text += "." + high_decimal

    try:
        low = to_number(low_text)
        high = to_number(high_text)
    except ValueError:
        return None

    if low > high:
        return None

    return {"low": low, "high": high}


def parse_result_line(line: str) -> dict[str, Any] | None:
    """Parse one line into a candidate laboratory result."""
    line = line.strip()
    if not line:
        return None

    # Capture the test name first, then the first numeric value.
    # The name can contain spaces, commas, slashes and digits.
    match = re.match(
        r"^\s*"
        r"(?P<test_name>[A-Za-z][A-Za-z0-9 /(),.%_-]*?)"
        r"\s*:?\s+"
        r"(?P<value>(?:<=|>=|<|>)?\s*-?\d[\d,]*(?:\.\d+)?)"
        r"(?P<remainder>.*)$",
        line,
    )

    if not match:
        return None

    test_name = match.group("test_name").strip(" :-\t")
    raw_value = match.group("value").strip()
    remainder = match.group("remainder").strip()

    value_match = VALUE_RE.match(raw_value)
    if not value_match or not test_name:
        return None

    try:
        value = to_number(value_match.group("number"))
    except ValueError:
        return None

    comparator = value_match.group("comparator")

    flag_match = re.search(
        r"\b(High|Low|Abnormal|Critical)\b",
        remainder,
        re.IGNORECASE,
    )
    flag = flag_match.group(1).lower() if flag_match else None

    reference_range = parse_reference_range(remainder)

    # Remove the reference interval and status flag before
    # looking for the measurement unit.
    remainder_for_unit = RANGE_RE.sub("", remainder)
    remainder_for_unit = re.sub(
        r"\b(High|Low|Abnormal|Critical)\b",
        "",
        remainder_for_unit,
        flags=re.IGNORECASE,
    )

    unit_match = UNIT_RE.search(remainder_for_unit)
    unit = unit_match.group(0) if unit_match else None

    return {
        "test_name": test_name,
        "value": value,
        "comparator": comparator,
        "unit": unit,
        "reference_range": reference_range,
        "flag": flag,
        "original_line": line,
        "needs_review": True,
    }


def parse_report_text(text: str) -> dict[str, Any]:
    """Parse extracted report text into candidate results."""
    if not isinstance(text, str):
        raise TypeError("Report text must be a string.")

    if not text.strip():
        raise ValueError("Report text is empty.")

    results = []
    unparsed_lines = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        result = parse_result_line(line)

        if result is None:
            unparsed_lines.append(line)
        else:
            results.append(result)

    return {
        "results": results,
        "unparsed_lines": unparsed_lines,
        "result_count": len(results),
        "parser_version": "0.5",
        "disclaimer": (
            "Extracted values are unverified candidates. Verify "
            "test names, values, units, flags and reference ranges "
            "against the original report. This parser does not "
            "provide a diagnosis."
        ),
    }


def parse_report_file(file_path: str) -> dict[str, Any]:
    """Parse a UTF-8 text file."""
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Report text file not found: {path}"
        )

    text = path.read_text(encoding="utf-8")
    return parse_report_text(text)
