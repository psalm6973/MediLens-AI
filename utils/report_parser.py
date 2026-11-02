
from pathlib import Path
from typing import Any
import re


# ============================================================
# 1. NUMBER AND ROW PATTERNS
# ============================================================

NUMBER = r"-?\d[\d,]*(?:\.\d+)?"

ROW_RE = re.compile(
    rf"^(?P<left>.*?)\s+"
    rf"(?P<value>{NUMBER})\s+"
    rf"(?P<right>.*)$"
)

RANGE_RE = re.compile(
    rf"(?P<low>{NUMBER})\s*(?:-|–|—|to)\s*"
    rf"(?P<high>{NUMBER})",
    re.IGNORECASE,
)

UNIT_RE = re.compile(
    r"(?<![A-Za-z])"
    r"(?:"
    r"millions?/cumm|"
    r"lakhs?/cumm|"
    r"cells?/cumm|"
    r"cells?/µl|"
    r"cells?/ul|"
    r"million/µl|"
    r"million/ul|"
    r"lakhs?/µl|"
    r"lakhs?/ul|"
    r"g/dl|g/di|g/l|gm%|"
    r"mg/dl|mg/di|"
    r"mmol/l|mmol/di|"
    r"umol/l|µmol/l|"
    r"ng/ml|pg/ml|"
    r"fl|fL|pg|"
    r"iu/l|u/l|"
    r"miu/l|"
    r"mm/hr|mm/hour|"
    r"seconds?|"
    r"minutes?|"
    r"%" 
    r")"
    r"(?![A-Za-z])",
    re.IGNORECASE,
)


# ============================================================
# 2. METADATA AND HEADER FILTERS
# ============================================================

METADATA_RE = re.compile(
    r"^(?:"
    r"ORDER NO|HH NO|ADM NO|NAME|PATIENT NAME|"
    r"AGE|SEX|GENDER|DATE|LOCATION|REFERRED BY|"
    r"SAMP\.? COLL|SAMPLE TYPE|WORK SHT|"
    r"MAIN LAB|DEPARTMENT|PHONE|CONSULTANT|"
    r"REPORT PRINTED|PRINT DATE|PAGE|SID|"
    r"COLLECTED|REGISTERED|RECEIVED|APPROVED|"
    r"BARCODE"
    r")\b",
    re.IGNORECASE,
)

HEADER_RE = re.compile(
    r"^(?:"
    r"TEST NAME|TEST|RESULT|RESULTS|UNITS?|"
    r"REFERENCE RANGE|BIOLOGICAL REFERENCE|"
    r"HAEMATOLOGY|HEMATOLOGY|"
    r"BIOCHEMISTRY|"
    r"CBC|COMPLETE BLOOD COUNT|"
    r"LIVER FUNCTION TEST|LFT|"
    r"KIDNEY FUNCTION TEST|KFT|RFT|"
    r"LIPID PROFILE|"
    r"DIFFERENTIAL COUNT|"
    r"PERIPHERAL SMEAR EXAMINATION|"
    r"URINE ROUTINE|"
    r"URINALYSIS"
    r")\b",
    re.IGNORECASE,
)

PAGE_RE = re.compile(
    r"^[.\s]*PAGE\s+\d+(?:\s+OF\s+\d+)?",
    re.IGNORECASE,
)


# ============================================================
# 3. CONTROLLED UNIT NORMALIZATION
# ============================================================

UNIT_CORRECTIONS = {
    "g/di": "g/dL",
    "g/dl": "g/dL",
    "g/l": "g/L",
    "gm%": "g/dL",
    "mg/di": "mg/dL",
    "mg/dl": "mg/dL",
    "mmol/l": "mmol/L",
    "umol/l": "µmol/L",
    "µmol/l": "µmol/L",
    "ng/ml": "ng/mL",
    "pg/ml": "pg/mL",
    "iu/l": "IU/L",
    "u/l": "U/L",
    "fl": "fL",
    "pg": "pg",
    "%": "%",
}


def normalize_unit(raw_unit: str | None):
    """Normalize known unit variations without guessing unknown units."""

    if not raw_unit:
        return None, False

    key = raw_unit.strip().lower()

    corrected = UNIT_CORRECTIONS.get(key)

    if corrected is None:
        return raw_unit.strip(), False

    return corrected, corrected != raw_unit


# ============================================================
# 4. BASIC HELPERS
# ============================================================

def to_number(value: str) -> float:
    return float(value.replace(",", "").strip())


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
    """Find standalone abnormality flags."""

    cleaned = RANGE_RE.sub("", text)
    cleaned = UNIT_RE.sub("", cleaned)

    tokens = re.findall(
        r"(?<![A-Za-z])"
        r"(?:H|L|HIGH|LOW|ABNORMAL|CRITICAL)"
        r"(?![A-Za-z])",
        cleaned,
        re.IGNORECASE,
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


def clean_test_name(name: str) -> str:
    """Clean a candidate test label without inventing a test name."""

    name = re.sub(r"\s+", " ", name).strip()
    name = name.strip(" :;|.-")

    return name


def is_valid_test_label(name: str) -> bool:
    """Reject empty labels and common report headings."""

    if len(name) < 2:
        return False

    if METADATA_RE.search(name):
        return False

    if HEADER_RE.search(name):
        return False

    if re.fullmatch(r"[\d\s.,:/-]+", name):
        return False

    return True


# ============================================================
# 5. PARSE ONE TABLE ROW
# ============================================================

def parse_table_row(line: str):

    match = ROW_RE.match(line.strip())

    if not match:
        return None

    left = clean_test_name(match.group("left"))
    raw_value = match.group("value")
    right = match.group("right").strip()

    if not is_valid_test_label(left):
        return None

    raw_unit = extract_unit(right)

    reference_range = extract_reference_range(right)
    flag = extract_flag(right)

    # A numeric value alone is not enough to identify a test result.
    # Require a recognised unit, reference range, or explicit flag.
    if not raw_unit and not reference_range and not flag:
        return None

    normalized_unit, unit_corrected = normalize_unit(raw_unit)

    value = to_number(raw_value)

    return {
        "left": left,
        "value": value,
        "raw_ocr_value": raw_value,
        "unit": normalized_unit,
        "raw_ocr_unit": raw_unit,
        "unit_correction_applied": unit_corrected,
        "flag": flag,
        "reference_range": reference_range,
        "original_line": line.strip(),
    }


# ============================================================
# 6. CREATE TEST ENTRY
# ============================================================

def create_test_entry(test_name: str, row: dict):

    return {
        "test_name": clean_test_name(test_name),

        "value": row["value"],
        "raw_ocr_value": row["raw_ocr_value"],

        "unit": row["unit"],
        "raw_ocr_unit": row["raw_ocr_unit"],
        "unit_correction_applied": row["unit_correction_applied"],

        "reference_range": row["reference_range"],
        "flag": row["flag"],

        "reference_status": check_reference_status(
            row["value"],
            row["reference_range"],
        ),

        "alternate_values": [],

        # Every OCR candidate requires verification.
        "needs_review": True,

        "correction_applied": row["unit_correction_applied"],

        "original_line": row["original_line"],
    }


# ============================================================
# 7. PARSE REPORT
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

    for line in lines:

        if METADATA_RE.search(line):
            continue

        if PAGE_RE.search(line):
            continue

        if HEADER_RE.search(line):
            continue

        if re.fullmatch(r"[-_|. ]+", line):
            continue

        row = parse_table_row(line)

        if row is None:
            unparsed_lines.append(line)
            continue

        # The label is taken from the report itself.
        # No fixed list of test names is required.
        test_name = row["left"]

        results.append(
            create_test_entry(test_name, row)
        )

    return {
        "results": results,

        "unassigned_values": [],

        "unparsed_lines": unparsed_lines,

        "result_count": len(results),

        "unassigned_value_count": 0,

        "parser_version": "2.0",

        "disclaimer": (
            "Extracted values are unverified OCR candidates. "
            "All test names, values, units and reference ranges "
            "must be checked against the original report. "
            "This parser does not provide medical diagnoses "
            "or treatment recommendations."
        ),
    }


# ============================================================
# 8. PARSE TEXT FILE
# ============================================================

def parse_report_file(file_path: str) -> dict[str, Any]:

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Report text file not found: {path}"
        )

    text = path.read_text(encoding="utf-8")

    return parse_report_text(text)
