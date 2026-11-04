
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
    r"millions?/cumm|lakhs?/cumm|cells?/cumm|"
    r"cells?/µl|cells?/ul|million/µl|million/ul|"
    r"lakhs?/µl|lakhs?/ul|"
    r"g/dl|g/di|git|g/l|gm%|"
    r"mg/dl|mg/di|mag/di|"
    r"mmol/l|mmol/di|"
    r"umol/l|umol/i|µmol/l|µmol/i|"
    r"ng/ml|pg/ml|fl|pg|"
    r"miu/l|iu/l|iu/t|1u/i|u/l|"
    r"mm/hr|mm/hour|seconds?|minutes?|%"
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
    r"SAMPLE(?:\s+NO|\s+ID|\s+TYPE)?|"
    r"WORK SHT|MAIN LAB|DEPARTMENT|PHONE|CONSULTANT|"
    r"REPORT PRINTED|PRINT DATE|PAGE|SID|"
    r"COLLECTED|REGISTERED|RECEIVED|APPROVED|BARCODE"
    r")\b",
    re.IGNORECASE,
)

HEADER_RE = re.compile(
    r"^(?:"
    r"TEST NAME|TEST|RESULT|RESULTS|UNITS?|"
    r"REFERENCE RANGE|BIOLOGICAL REFERENCE|"
    r"HAEMATOLOGY|HEMATOLOGY|BIOCHEMISTRY|"
    r"CBC|COMPLETE BLOOD COUNT|"
    r"LIVER FUNCTION TEST|LFT|"
    r"KIDNEY FUNCTION TEST|KFT|RFT|"
    r"LIPID PROFILE|DIFFERENTIAL COUNT|"
    r"PERIPHERAL SMEAR EXAMINATION|"
    r"URINE ROUTINE|URINALYSIS"
    r")\b",
    re.IGNORECASE,
)

PAGE_RE = re.compile(
    r"^\s*PAGE\s+\d+(?:\s+OF\s+\d+)?",
    re.IGNORECASE,
)


# ============================================================
# 3. UNIT NORMALIZATION
# ============================================================

UNIT_CORRECTIONS = {
    "g/di": "g/dL",
    "git": "g/L",
    "g/dl": "g/dL",
    "g/l": "g/L",
    "gm%": "g/dL",

    "mg/di": "mg/dL",
    "mag/di": "mg/dL",
    "mg/dl": "mg/dL",

    "mmol/l": "mmol/L",
    "mmol/di": "mmol/L",

    "umol/l": "µmol/L",
    "umol/i": "µmol/L",
    "µmol/l": "µmol/L",
    "µmol/i": "µmol/L",

    "ng/ml": "ng/mL",
    "pg/ml": "pg/mL",

    "iu/l": "IU/L",
    "iu/t": "IU/L",
    "1u/i": "IU/L",
    "u/l": "U/L",
    "miu/l": "mIU/L",

    "fl": "fL",
    "pg": "pg",

    "seconds": "Seconds",
    "second": "Seconds",
    "minutes": "Minutes",
    "minute": "Minutes",

    "%": "%",
}


def normalize_unit(raw_unit: str | None):
    if not raw_unit:
        return None, False

    key = raw_unit.strip().lower()
    corrected = UNIT_CORRECTIONS.get(key)

    if corrected is None:
        return raw_unit.strip(), False

    return corrected, corrected.lower() != key


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
    return match.group(0) if match else None


def extract_flag(text: str):
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
    name = re.sub(r"\s+", " ", name).strip()
    return name.strip(" :;|.-")


def is_valid_test_label(name: str) -> bool:
    if len(name) < 2:
        return False

    if METADATA_RE.search(name) or HEADER_RE.search(name):
        return False

    if re.fullmatch(r"[\d\s.,:/-]+", name):
        return False

    return True


# ============================================================
# 5. TEST-NAME NORMALIZATION
# ============================================================

def normalize_test_name(name: str) -> str:
    name = clean_test_name(name)

    name = re.sub(
        r"\b(?:conventional|s\.?\s*i\.?)\b",
        "",
        name,
        flags=re.IGNORECASE,
    )

    name = re.sub(
        r"\b(?:serum|plasma|enzymatic|calculated)\b",
        "",
        name,
        flags=re.IGNORECASE,
    )

    name = re.sub(r"\s+", " ", name).strip(" :;|.-")

    return name


def is_si_row(label: str) -> bool:
    return bool(
        re.search(r"\bS\.?\s*I\.?\b", label, re.IGNORECASE)
    )


def is_conventional_row(label: str) -> bool:
    return bool(
        re.search(r"\bconventional\b", label, re.IGNORECASE)
    )


# ============================================================
# 6. PARSE ONE TABLE ROW
# ============================================================

def parse_table_row(line: str):

    line = line.strip()

    # Special OCR case:
    # "Serum Enzymatic 5, I. 76.00 IU/L ..."
    # Here "5, I." may represent "S.I."
    # Do not treat the 5 as a measured value.

    si_noise = re.match(
        r"^(?P<label>(?:serum|plasma)\b.*?)"
        r"\s+5\s*,\s*I\.?\s+"
        rf"(?P<value>{NUMBER})\b"
        r"(?P<right>.*)$",
        line,
        re.IGNORECASE,
    )

    if si_noise:
        left = clean_test_name(
            si_noise.group("label") + " S.I."
        )
        raw_value = si_noise.group("value")
        right = si_noise.group("right").strip()
        label_noise_detected = True

    else:
        match = ROW_RE.match(line)

        if not match:
            return None

        left = clean_test_name(match.group("left"))
        raw_value = match.group("value")
        right = match.group("right").strip()
        label_noise_detected = False

    if not is_valid_test_label(left):
        return None

    raw_unit = extract_unit(right)
    reference_range = extract_reference_range(right)
    flag = extract_flag(right)

    if not raw_unit and not reference_range and not flag:
        return None

    normalized_unit, unit_corrected = normalize_unit(raw_unit)

    # Remove reference range, unit and flags before
    # checking for other possible result numbers.

    remaining = RANGE_RE.sub("", right)

    if raw_unit:
        remaining = UNIT_RE.sub("", remaining, count=1)

    remaining = re.sub(
        r"(?<![A-Za-z])"
        r"(?:H|L|HIGH|LOW|ABNORMAL|CRITICAL)"
        r"(?![A-Za-z])",
        "",
        remaining,
        flags=re.IGNORECASE,
    )

    candidates = [to_number(raw_value)]

    for candidate in re.findall(NUMBER, remaining):
        number = to_number(candidate)

        if number not in candidates:
            candidates.append(number)

    value_ambiguous = len(candidates) > 1

    if label_noise_detected:
        value_ambiguous = False

    value = to_number(raw_value)

    return {
        "left": left,
        "normalized_name": normalize_test_name(left),

        "value": value,
        "raw_ocr_value": raw_value,
        "value_candidates": candidates,
        "value_ambiguous": value_ambiguous,

        "unit": normalized_unit,
        "raw_ocr_unit": raw_unit,
        "unit_correction_applied": unit_corrected,

        "flag": flag,
        "reference_range": reference_range,

        "is_si": is_si_row(left),
        "is_conventional": is_conventional_row(left),

        "original_line": line,
    }


# ============================================================
# 7. CREATE TEST ENTRY
# ============================================================

def create_test_entry(test_name: str, row: dict):

    reasons = []

    if row["value_ambiguous"]:
        reasons.append("Multiple numeric candidates detected")

    needs_review = row["value_ambiguous"]

    return {
        "test_name": clean_test_name(test_name),

        "value": row["value"],
        "raw_ocr_value": row["raw_ocr_value"],
        "value_candidates": row["value_candidates"],
        "value_ambiguous": row["value_ambiguous"],

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

        "needs_review": needs_review,
        "needs_review_reasons": reasons,

        "correction_applied": row["unit_correction_applied"],
        "original_line": row["original_line"],
    }


# ============================================================
# 8. GROUP CONVENTIONAL AND SI REPRESENTATIONS
# ============================================================

def attach_alternate_value(primary: dict, alternate: dict):
    """
    Preserve the second representation as an alternate.
    Never overwrite the primary result.
    """

    alternate_needs_review = alternate["needs_review"]

    primary["alternate_values"].append({
        "value": alternate["value"],
        "raw_ocr_value": alternate["raw_ocr_value"],
        "value_candidates": alternate["value_candidates"],
        "value_ambiguous": alternate.get("value_ambiguous", False),

        "unit": alternate["unit"],
        "raw_ocr_unit": alternate["raw_ocr_unit"],

        "reference_range": alternate["reference_range"],
        "flag": alternate["flag"],
        "reference_status": alternate["reference_status"],

        "unit_correction_applied": alternate["unit_correction_applied"],
        "needs_review": alternate_needs_review,
        "needs_review_reasons": alternate["needs_review_reasons"],

        "original_line": alternate["original_line"],
    })

    # Different numeric representations are not automatically
    # errors because their units may differ.
    # Preserve them without choosing which is correct.

    if alternate_needs_review:
        primary["needs_review"] = True

        for reason in alternate["needs_review_reasons"]:
            if reason not in primary["needs_review_reasons"]:
                primary["needs_review_reasons"].append(reason)


def group_alternate_rows(results: list[dict]) -> list[dict]:
    """
    Group serum/plasma method rows with the preceding test.
    Preserve the original row as an alternate.
    """

    grouped = []
    previous_entry = None

    for entry in results:

        label = entry["test_name"].strip()

        is_method_row = bool(
            re.match(
                r"^(?:serum|plasma)\b",
                label,
                re.IGNORECASE,
            )
        )

        if is_method_row and previous_entry is not None:
            attach_alternate_value(previous_entry, entry)
            continue

        grouped.append(entry)
        previous_entry = entry

    return grouped


# ============================================================
# 9. PARSE REPORT
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

        entry = create_test_entry(row["left"], row)
        results.append(entry)

    results = group_alternate_rows(results)

    return {
        "results": results,

        "unassigned_values": [],
        "unparsed_lines": unparsed_lines,

        "result_count": len(results),
        "unassigned_value_count": 0,

        "parser_version": "3.3",

        "disclaimer": (
            "Extracted values are unverified OCR candidates. "
            "All test names, values, units and reference ranges "
            "must be checked against the original report. "
            "This parser does not provide medical diagnoses "
            "or treatment recommendations."
        ),
    }


# ============================================================
# 10. PARSE TEXT FILE
# ============================================================

def parse_report_file(file_path: str) -> dict[str, Any]:

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Report text file not found: {path}"
        )

    text = path.read_text(encoding="utf-8")

    return parse_report_text(text)
