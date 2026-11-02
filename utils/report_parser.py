
from pathlib import Path
from typing import Any
import re


# ============================================================
# 1. PATTERNS
# ============================================================

NUMBER = r"-?\d[\d,]*(?:\.\d+)?"

ROW_RE = re.compile(
    rf"^(?P<left>.*?)\s+"
    rf"(?P<value>{NUMBER})\s+"
    rf"(?P<right>.*)$"
)

RANGE_RE = re.compile(
    rf"(?P<low>{NUMBER})\s*(?:-|–|—|to)\s*(?P<high>{NUMBER})",
    re.IGNORECASE
)

UNIT_RE = re.compile(
    r"g/dl|g/di|g/l|gif|mg/dl|mg/d!|umol/l|umol/i|"
    r"µmol/l|u/l|ua|iu/l|ius|iuu/l|1uU/|%"
    r"g/dl|g/di|g/l|gil|gif|mg/dl|mg/d!|umol/l|umol/i|",
    re.IGNORECASE
)

METADATA_RE = re.compile(
    r"^(ORDER NO|HH NO|ADM NO|NAME|AGE|SEX|DATE|"
    r"LOCATION|REFERRED BY|SAMP\. COLL|WORK SHT|"
    r"MAIN LAB|DEPARTMENT|BIOCHEMISTRY|PHONE|"
    r"CONSULTANT|REPORT PRINTED|PAGE)\b",
    re.IGNORECASE
)

PAGE_RE = re.compile(
    r"^[.\s]*PAGE\s+\d+\s+OF\s+\d+",
    re.IGNORECASE
)

KNOWN_TEST_NAMES = [
    "Total Protein",
    "Albumin",
    "Globulin (calculated)",
    "A/G Ratio (calculated)",
    "AIG Ratio (calculated)",
    "Bilirubin(Total)",
    "Bilirubin (Total)",
    "Alkaline Phosphatase",
    "SGOT",
    "SGPT",
]


# ============================================================
# 2. CONTROLLED OCR NORMALIZATION
# ============================================================

UNIT_CORRECTIONS = {
    "gif": "g/L",
    "g/di": "g/dL",
    "g/dl": "g/dL",
    "g/l": "g/L",
    "mg/d!": "mg/dL",
    "mg/dl": "mg/dL",
    "umol/i": "µmol/L",
    "umol/l": "µmol/L",
    "µmol/l": "µmol/L",
    "ua": "U/L",
    "u/l": "U/L",
    "ius": "IU/L",
    "iu/l": "IU/L",
    "iuu/l": "IU/L",
    "1uu/": "IU/L",
    "1uU/": "IU/L",
    "%": "%",
    "gil": "g/L",
}


def normalize_unit(raw_unit: str | None):
    """Normalize only known OCR unit variations."""

    if not raw_unit:
        return None, False

    key = raw_unit.strip().lower()

    corrected = UNIT_CORRECTIONS.get(key)

    if corrected is None:
        return raw_unit, False

    return corrected, corrected != raw_unit


# ============================================================
# 3. BASIC HELPERS
# ============================================================

def to_number(value: str) -> float:
    return float(value.replace(",", "").strip())


def normalize_test_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()

    replacements = {
        "AIG Ratio (calculated)": "A/G Ratio (calculated)",
        "AIG Ratio": "A/G Ratio",
        "Bilirubin(Total)": "Bilirubin (Total)",
    }

    return replacements.get(name, name)


def find_test_name(left: str):
    normalized = re.sub(r"\s+", " ", left).strip()

    for name in sorted(KNOWN_TEST_NAMES, key=len, reverse=True):
        if normalized.lower().startswith(name.lower()):
            return name

    return None


def extract_reference_range(text: str):
    match = RANGE_RE.search(text)

    if not match:
        return None

    low = to_number(match.group("low"))
    high = to_number(match.group("high"))

    if low > high:
        return None

    return {
        "type": "range",
        "low": low,
        "high": high,
    }


def extract_unit(text: str):
    match = UNIT_RE.search(text)

    if not match:
        return None

    return match.group(0)


def extract_flag(text: str):
    """Find standalone flags without mistaking U/l for Low."""

    cleaned = RANGE_RE.sub("", text)
    cleaned = UNIT_RE.sub("", cleaned)

    tokens = re.findall(
        r"(?<![A-Za-z])(?:H|L|HIGH|LOW|ABNORMAL|CRITICAL)"
        r"(?![A-Za-z])",
        cleaned,
        re.IGNORECASE
    )

    if not tokens:
        return None

    flag = tokens[0].lower()

    if flag == "h":
        return "high"

    if flag == "l":
        return "low"

    return flag


def check_reference_status(value, reference_range):
    if not reference_range:
        return "unknown"

    if value < reference_range["low"]:
        return "below"

    if value > reference_range["high"]:
        return "above"

    return "within"


# ============================================================
# 4. PARSE ONE TABLE ROW
# ============================================================

def parse_table_row(line: str):

    match = ROW_RE.match(line.strip())

    if not match:
        return None

    left = match.group("left").strip()
    raw_value = match.group("value")
    right = match.group("right").strip()

    raw_unit = extract_unit(right)
    normalized_unit, unit_corrected = normalize_unit(raw_unit)

    value = to_number(raw_value)

    return {
        "left": left,
        "value": value,
        "raw_ocr_value": raw_value,
        "unit": normalized_unit,
        "raw_ocr_unit": raw_unit,
        "unit_correction_applied": unit_corrected,
        "flag": extract_flag(right),
        "reference_range": extract_reference_range(right),
        "original_line": line.strip(),
    }


# ============================================================
# 5. CREATE TEST ENTRY
# ============================================================

def create_test_entry(test_name: str, row: dict):

    return {
        "test_name": normalize_test_name(test_name),

        "value": row["value"],
        "raw_ocr_value": row["raw_ocr_value"],

        "unit": row["unit"],
        "raw_ocr_unit": row["raw_ocr_unit"],
        "unit_correction_applied": row["unit_correction_applied"],

        "reference_range": row["reference_range"],
        "flag": row["flag"],

        "reference_status": check_reference_status(
            row["value"],
            row["reference_range"]
        ),

        "alternate_values": [],

        "needs_review": True,
        "correction_applied": row["unit_correction_applied"],
        "original_line": row["original_line"],
    }


# ============================================================
# 6. PARSE REPORT
# ============================================================

def parse_report_text(text: str) -> dict[str, Any]:

    if not isinstance(text, str):
        raise TypeError("Report text must be a string.")

    if not text.strip():
        raise ValueError("Report text is empty.")

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]

    results = []
    unparsed_lines = []
    current_test = None

    def save_current():
        nonlocal current_test

        if current_test is not None:
            results.append(current_test)
            current_test = None

    for line in lines:

        if METADATA_RE.search(line) or PAGE_RE.search(line):
            continue

        if re.fullmatch(r"[-_|. ]+", line):
            continue

        if line.lower() in {
            "test result units status reference range",
            "liver profile",
            "serum",
        }:
            continue

        row = parse_table_row(line)

        if row is None:
            unparsed_lines.append(line)
            continue

        left = row["left"]

        # A recognized test name starts a new entry.
        test_name = find_test_name(left)

        if test_name:
            save_current()
            current_test = create_test_entry(test_name, row)
            continue

        # A Conventional row can introduce another test.
        conventional_match = re.search(
            r"\bConventional\b",
            left,
            re.IGNORECASE
        )

        if conventional_match:
            save_current()

            test_name = left[:conventional_match.start()].strip()

            if len(test_name) >= 3:
                current_test = create_test_entry(test_name, row)
            else:
                unparsed_lines.append(line)

            continue

        # Other rows are attached as alternate values.
        if current_test is not None:

            current_test["alternate_values"].append({
                "value": row["value"],
                "raw_ocr_value": row["raw_ocr_value"],

                "unit": row["unit"],
                "raw_ocr_unit": row["raw_ocr_unit"],
                "unit_correction_applied": row[
                    "unit_correction_applied"
                ],

                "reference_range": row["reference_range"],
                "flag": row["flag"],

                "reference_status": check_reference_status(
                    row["value"],
                    row["reference_range"]
                ),

                "original_line": row["original_line"],
                "needs_review": True,
            })

            if row["unit_correction_applied"]:
                current_test["correction_applied"] = True

            continue

        unparsed_lines.append(line)

    save_current()

    return {
        "results": results,
        "unassigned_values": [],
        "unparsed_lines": unparsed_lines,
        "result_count": len(results),
        "unassigned_value_count": 0,
        "parser_version": "1.2",
        "disclaimer": (
            "Extracted values are unverified candidates. "
            "Normalized units are controlled OCR corrections. "
            "Verify all values, units and reference ranges against "
            "the original report. This parser does not provide "
            "medical advice or diagnoses."
        ),
    }


# ============================================================
# 7. PARSE TEXT FILE
# ============================================================

def parse_report_file(file_path: str) -> dict[str, Any]:

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Report text file not found: {path}"
        )

    text = path.read_text(encoding="utf-8")

    return parse_report_text(text)
