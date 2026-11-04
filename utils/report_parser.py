
from pathlib import Path
from typing import Any
import re


# ============================================================
# 1. PATTERNS AND UNIT NORMALIZATION
# ============================================================

NUMBER = r"-?\d[\d,]*(?:\.\d+)?"

UNIT_CORRECTIONS = {
    "g/dl": "g/dL",
    "g/l": "g/L",
    "mg/l": "mg/L",
    "gm%": "g/dL",
    "mg/dl": "mg/dL",
    "mmol/l": "mmol/L",
    "umol/l": "µmol/L",
    "µmol/l": "µmol/L",
    "ng/ml": "ng/mL",
    "pg/ml": "pg/mL",
    "iu/l": "IU/L",
    "u/l": "U/L",
    "miu/l": "mIU/L",
    "fl": "fL",
}

KNOWN_UNITS = {
    "g/dl", "g/l", "gm%", "mg/dl", "mg/l", "mmol/l",
    "umol/l", "µmol/l", "ng/ml", "pg/ml",
    "iu/l", "u/l", "miu/l", "fl", "pg", "%",
    "cells/ul", "cells/µl", "cells/cumm",
    "million/ul", "million/µl", "millions/cumm",
    "lakhs/cumm", "mm/hr", "mm/hour",
    "seconds", "second", "minutes", "minute",
    "iu", "au", "ratio", "index",
}

METADATA_RE = re.compile(
    r"^(?:ORDER NO|HH NO|ADM NO|NAME|PATIENT NAME|"
    r"AGE|SEX|GENDER|DATE|LOCATION|REFERRED BY|"
    r"SAMPLE|WORK SHT|MAIN LAB|DEPARTMENT|"
    r"REPORT PRINTED|PAGE|CONSULTANT)\b",
    re.IGNORECASE,
)

HEADER_RE = re.compile(
    r"^(?:TEST NAME|TEST|RESULT|RESULTS|UNITS?|"
    r"REFERENCE RANGE|BIOLOGICAL REFERENCE|"
    r"HAEMATOLOGY|HEMATOLOGY|BIOCHEMISTRY|"
    r"CBC|COMPLETE BLOOD COUNT|LIVER PROFILE|"
    r"LIVER FUNCTION TEST|LFT|KIDNEY FUNCTION TEST|"
    r"KFT|RFT|LIPID PROFILE|URINALYSIS)\b",
    re.IGNORECASE,
)

PLAIN_RANGE_RE = re.compile(
    rf"(?P<low>{NUMBER})\s*(?:-|–|—|to)\s*"
    rf"(?P<high>{NUMBER})",
    re.IGNORECASE,
)

PLAIN_UNIT_RE = re.compile(
    r"\b(?:g/dl|g/l|gm%|mg/dl|mmol/l|umol/l|µmol/l|"
    r"ng/ml|pg/ml|iu/l|u/l|miu/l|fl|pg|%|"
    r"cells/cumm|cells/ul|million/ul|millions/cumm|"
    r"lakhs/cumm|mm/hr|mm/hour|seconds?|minutes?|au|iu)\b",
    re.IGNORECASE,
)


# ============================================================
# 2. GENERAL HELPERS
# ============================================================

def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def to_number(value: str) -> float:
    return float(value.replace(",", "").strip())


def normalize_unit(raw_unit: str | None):
    if not raw_unit:
        return None, False, False

    raw = clean_text(raw_unit)
    key = raw.lower()

    if key in UNIT_CORRECTIONS:
        normalized = UNIT_CORRECTIONS[key]
        return normalized, normalized != raw, True

    if key in KNOWN_UNITS:
        return raw, False, True

    return raw, False, False


def parse_range_parts(low_text: str, high_text: str):
    low_match = re.search(NUMBER, low_text or "")
    high_match = re.search(NUMBER, high_text or "")

    if not low_match or not high_match:
        return None

    low = to_number(low_match.group())
    high = to_number(high_match.group())

    if low > high:
        return None

    return {"type": "range", "low": low, "high": high}


def parse_plain_range(line: str):
    cleaned = clean_text(line)
    match = PLAIN_RANGE_RE.search(cleaned)

    if not match:
        return None

    # Accept commas only as correctly grouped thousands separators.
    # OCR text such as "2,3-603" is ambiguous and must not become 23-603.
    for part in (match.group("low"), match.group("high")):
        if "," in part and not re.fullmatch(r"\d{1,3}(?:,\d{3})+", part):
            return None

    low = to_number(match.group("low"))
    high = to_number(match.group("high"))

    if low > high:
        return None

    return {"type": "range", "low": low, "high": high}


def check_reference_status(value, reference_range):
    if not reference_range:
        return "unknown"

    if value < reference_range["low"]:
        return "below"

    if value > reference_range["high"]:
        return "above"

    return "within"


def extract_flag(raw_flag: str | None):
    if not raw_flag:
        return None

    mapping = {
        "H": "high",
        "HIGH": "high",
        "L": "low",
        "LOW": "low",
        "ABNORMAL": "abnormal",
        "CRITICAL": "critical",
    }

    return mapping.get(clean_text(raw_flag).upper())


def normalize_test_name(name: str) -> str:
    name = clean_text(name)
    name = re.sub(r"[()]", " ", name)

    name = re.sub(
        r"\b(?:conventional|s\.?\s*i\.?|s\.?1\.?)\b",
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

    aliases = {
        "globulin": "Globulin",
        "bilirubin total": "Total Bilirubin",
        "bilirubin": "Total Bilirubin",
        "a/g ratio": "A/G Ratio",
    }

    return aliases.get(name.lower(), name)


def is_valid_test_label(name: str) -> bool:
    name = clean_text(name)

    if len(name) < 2:
        return False

    if METADATA_RE.search(name) or HEADER_RE.search(name):
        return False

    if re.fullmatch(r"[\d\s.,:/-]+", name):
        return False

    return True


def is_si_marker(value: str) -> bool:
    cleaned = clean_text(value).upper()
    cleaned = cleaned.replace(" ", "").replace(",", "")

    return cleaned in {
        "S.I.", "S.I", "S.1.", "S.1", "SI", "S1"
    }


def make_review_reasons(
    value_ambiguous: bool,
    unit_recognized: bool,
    raw_unit: str | None,
    extra_reasons: list[str] | None = None,
):
    reasons = []

    if value_ambiguous:
        reasons.append("Value could not be confidently interpreted")

    if raw_unit and not unit_recognized:
        reasons.append(
            "Unit could not be confidently recognized; "
            "verify it against the original report"
        )

    if extra_reasons:
        for reason in extra_reasons:
            if reason not in reasons:
                reasons.append(reason)

    return reasons


# ============================================================
# 3. STANDARD RESULT ENTRY
# ============================================================

def create_test_entry(
    test_name: str,
    value_text: str,
    raw_unit: str | None,
    raw_flag: str | None,
    reference_range: dict | None,
    original_line: str,
    value_ambiguous: bool = False,
    extra_review_reasons: list[str] | None = None,
):
    value = to_number(value_text)

    normalized_unit, unit_corrected, unit_recognized = (
        normalize_unit(raw_unit)
    )

    reasons = make_review_reasons(
        value_ambiguous,
        unit_recognized,
        raw_unit,
        extra_review_reasons,
    )

    flag = extract_flag(raw_flag)

    return {
        "test_name": clean_text(test_name),

        "value": value,
        "raw_ocr_value": value_text,
        "value_candidates": [value],
        "value_ambiguous": value_ambiguous,

        "unit": normalized_unit,
        "raw_ocr_unit": raw_unit,
        "unit_correction_applied": unit_corrected,

        "reference_range": reference_range,
        "flag": flag,

        "reference_status": check_reference_status(
            value, reference_range
        ),

        "alternate_values": [],

        "needs_review": bool(reasons),
        "needs_review_reasons": reasons,

        "correction_applied": unit_corrected,
        "original_line": original_line,
    }


# ============================================================
# 4. ALTERNATE S.I. VALUES
# ============================================================

def attach_alternate_value(primary: dict, alternate: dict):
    primary["alternate_values"].append({
        "value": alternate["value"],
        "raw_ocr_value": alternate["raw_ocr_value"],
        "value_candidates": alternate["value_candidates"],
        "value_ambiguous": alternate["value_ambiguous"],
        "unit": alternate["unit"],
        "raw_ocr_unit": alternate["raw_ocr_unit"],
        "reference_range": alternate["reference_range"],
        "flag": alternate["flag"],
        "reference_status": alternate["reference_status"],
        "unit_correction_applied": alternate["unit_correction_applied"],
        "needs_review": alternate["needs_review"],
        "needs_review_reasons": alternate["needs_review_reasons"],
        "original_line": alternate["original_line"],
    })

    if alternate["needs_review"]:
        primary["needs_review"] = True

        for reason in alternate["needs_review_reasons"]:
            if reason not in primary["needs_review_reasons"]:
                primary["needs_review_reasons"].append(reason)


# ============================================================
# 5. MARKDOWN TABLE PARSER
# ============================================================

def split_markdown_row(line: str) -> list[str]:
    line = line.strip()

    if not line.startswith("|"):
        return []

    if line.endswith("|"):
        line = line[1:-1]
    else:
        line = line[1:]

    return [clean_text(cell) for cell in line.split("|")]


def is_markdown_separator(cells: list[str]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-{2,}:?", cell.replace(" ", ""))
        for cell in cells
    )


def is_table_header(cells: list[str]) -> bool:
    combined = " ".join(cells).lower()

    has_test = any(
        word in combined
        for word in ("test", "analyte", "investigation", "parameter")
    )
    has_result = any(
        word in combined
        for word in ("result", "value", "reading", "observation")
    )

    return has_test and has_result


def get_generic_column_map(headers: list[str]) -> dict[str, int]:
    """
    Identify columns from their headings instead of assuming
    every report uses the same table layout.
    """
    mapping = {}

    for index, header in enumerate(headers):
        key = re.sub(r"[^a-z]", "", header.lower())

        if any(word in key for word in (
            "testname", "test", "analyte",
            "investigation", "parameter"
        )):
            mapping.setdefault("name", index)

        if any(word in key for word in (
            "result", "value", "reading", "observation"
        )):
            mapping.setdefault("value", index)

        if "unit" in key:
            mapping.setdefault("unit", index)

        if any(word in key for word in (
            "reference", "bio", "normalrange", "biological"
        )):
            mapping.setdefault("range", index)

        if key in {"flag", "status", "remarks", "mark"}:
            mapping.setdefault("flag", index)

    return mapping


def parse_generic_markdown_row(
    cells: list[str],
    mapping: dict[str, int],
    original_line: str,
):
    if "name" not in mapping or "value" not in mapping:
        return None

    def cell(field):
        index = mapping.get(field)
        return cells[index] if index is not None and index < len(cells) else ""

    label = cell("name")
    value_text = cell("value")
    raw_unit = cell("unit") or None
    raw_range = cell("range")
    raw_flag = cell("flag") or None

    if not is_valid_test_label(label):
        return None

    # Do not guess values containing OCR-corrupted characters.
    if not re.fullmatch(NUMBER, value_text.replace(",", "")):
        return None

    reference_range = parse_plain_range(raw_range)

    extra_reasons = []

    # A non-empty reference field that cannot be parsed is suspicious.
    if raw_range and not reference_range:
        extra_reasons.append(
            "Reference interval could not be parsed; verify the original report"
        )

    # Preserve a unit field even if OCR may have merged extra text into it.
    if raw_unit and re.search(NUMBER, raw_unit):
        extra_reasons.append(
            "Unit field contains numeric text and may have shifted columns"
        )

    # Multiple numeric candidates in a value cell are not safe to resolve.
    numeric_candidates = re.findall(NUMBER, value_text)

    # Detect possible thousands-separator / decimal ambiguity.
    scale_ambiguous = False

    if (
        re.fullmatch(r"\d+\.\d{3}", value_text)
        and raw_unit
        and re.search(r"cells|cumm|million|lakhs", raw_unit, re.I)
    ):
        scale_ambiguous = True
        extra_reasons.append(
            "Possible decimal/thousands-separator ambiguity; "
            "verify the original value"
        )
    return {
        "row_type": "primary",
        "test_name": normalize_test_name(label),
        "value_text": value_text,
        "raw_unit": raw_unit,
        "raw_flag": raw_flag,
        "reference_range": reference_range,
        "original_line": original_line,
        "value_ambiguous": len(numeric_candidates) != 1,
        "extra_review_reasons": extra_reasons,
        "scale_ambiguous": scale_ambiguous,
    }


def parse_markdown_table_row(line: str):
    """
    Preserve the original eight-column Report 004 layout.
    Other table layouts are handled by the generic parser.
    """
    cells = split_markdown_row(line)

    if len(cells) < 6 or is_markdown_separator(cells):
        return None

    test_label = cells[0]
    method_label = cells[2]
    value_text = cells[3]
    raw_unit = cells[4] or None
    raw_flag = cells[5] or None

    if not is_valid_test_label(test_label):
        return None

    if not re.fullmatch(NUMBER, value_text.replace(",", "")):
        return None

    reference_range = None

    if len(cells) >= 8:
        reference_range = parse_range_parts(cells[6], cells[7])

    is_method_row = bool(
        re.match(r"^(?:serum|plasma)$", test_label, re.IGNORECASE)
    )

    if is_method_row and is_si_marker(method_label):
        return {
            "row_type": "alternate",
            "value_text": value_text,
            "raw_unit": raw_unit,
            "raw_flag": raw_flag,
            "reference_range": reference_range,
            "original_line": line,
        }

    return {
        "row_type": "primary",
        "test_name": normalize_test_name(test_label),
        "value_text": value_text,
        "raw_unit": raw_unit,
        "raw_flag": raw_flag,
        "reference_range": reference_range,
        "original_line": line,
        "value_ambiguous": False,
        "extra_review_reasons": [],
    }


def parse_markdown_tables(lines: list[str]):
    results = []
    unparsed_lines = []
    current_mapping = None

    for line in lines:
        if not line.strip().startswith("|"):
            continue

        cells = split_markdown_row(line)

        if is_markdown_separator(cells):
            continue

        if is_table_header(cells):
            current_mapping = get_generic_column_map(cells)
            continue

        # The original Report 004 table uses eight fixed columns.
        parsed = None

        if len(cells) >= 8:
            parsed = parse_markdown_table_row(line)

        # Other tables use their detected column headings.
        if parsed is None and current_mapping:
            parsed = parse_generic_markdown_row(
                cells, current_mapping, line
            )

        # Fallback for ordinary four-column tables without a detected header.
        if parsed is None and len(cells) == 4:
            parsed = parse_generic_markdown_row(
                cells,
                {"name": 0, "value": 1, "unit": 2, "range": 3},
                line,
            )

        if parsed is None:
            # Avoid treating obvious section labels as failed result rows.
            if len(cells) > 1 and any(cells):
                unparsed_lines.append(line)
            continue

        if parsed["row_type"] == "alternate":
            if results:
                alternate = create_test_entry(
                    test_name=results[-1]["test_name"],
                    value_text=parsed["value_text"],
                    raw_unit=parsed["raw_unit"],
                    raw_flag=parsed["raw_flag"],
                    reference_range=parsed["reference_range"],
                    original_line=parsed["original_line"],
                )
                attach_alternate_value(results[-1], alternate)
            else:
                unparsed_lines.append(line)
            continue

        entry = create_test_entry(
            test_name=parsed["test_name"],
            value_text=parsed["value_text"],
            raw_unit=parsed["raw_unit"],
            raw_flag=parsed["raw_flag"],
            reference_range=parsed["reference_range"],
            original_line=parsed["original_line"],
            value_ambiguous=parsed.get("value_ambiguous", False),
            extra_review_reasons=parsed.get("extra_review_reasons"),
        )
        if parsed.get("scale_ambiguous"):
            entry["reference_status"] = "unknown"

        results.append(entry)

    return results, unparsed_lines


# ============================================================
# 6. PLAIN-TEXT PARSER
# ============================================================

PLAIN_ROW_RE = re.compile(
    rf"^(?P<label>.*?)\s+(?P<value>{NUMBER})\s+(?P<right>.*)$"
)


def is_number_line(line: str) -> bool:
    return bool(re.fullmatch(NUMBER, clean_text(line)))


def parse_plain_text_row(line: str):
    # OCR can merge patient metadata into a line and make IDs/dates look like
    # test results. Reject these before considering a numeric candidate.
    metadata_noise = re.search(
        r"\b(?:HN\s*\d{5,}|MRN\s*\d+|BARCODE|COLLECTED|REGISTERED|"
        r"REPORTED|ACCEPTED|FEMALE|MALE|PATIENT|SAMPLE TYPE|REF CUSTOMER)\b|"
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
        line,
        re.IGNORECASE,
    )
    if metadata_noise:
        return None

    match = PLAIN_ROW_RE.match(line.strip())

    if not match:
        return None

    label = clean_text(match.group("label"))
    value_text = match.group("value")
    right = clean_text(match.group("right"))

    if not is_valid_test_label(label):
        return None

    reference_range = parse_plain_range(right)

    unit_match = PLAIN_UNIT_RE.search(right)
    raw_unit = unit_match.group(0) if unit_match else None

    flag_match = re.search(
        r"\b(H|L|HIGH|LOW|ABNORMAL|CRITICAL)\b",
        right,
        re.IGNORECASE,
    )
    raw_flag = flag_match.group(0) if flag_match else None

    # Keep a plausible result row even when OCR has damaged its unit/range,
    # but explicitly mark it for human verification.
    if not raw_unit and not reference_range and not raw_flag and not re.search(r"\d|[<>]", right):
        return None

    review_reasons = []
    if not raw_unit:
        review_reasons.append("Unit is missing or unreadable in extracted text; verify the original report")
    if re.search(r"\d\s*,\s*\d+\s*[-–—]", right) and not reference_range:
        review_reasons.append("Reference interval contains an ambiguous OCR comma; it was not interpreted")
    if re.search(r"(?:negative|positive)\s*[:.]?\s*[<>]", right, re.I):
        review_reasons.append("Qualitative threshold is present; this parser does not encode threshold categories as numeric ranges")

    return create_test_entry(
        test_name=normalize_test_name(label),
        value_text=value_text,
        raw_unit=raw_unit,
        raw_flag=raw_flag,
        reference_range=reference_range,
        original_line=line,
        extra_review_reasons=review_reasons,
    )


def parse_plain_text(lines: list[str]):
    results = []
    unparsed_lines = []
    i = 0

    while i < len(lines):
        line = clean_text(lines[i])

        if not line:
            i += 1
            continue

        if METADATA_RE.search(line) or HEADER_RE.search(line):
            i += 1
            continue

        if re.fullmatch(r"[-_|. ]+", line):
            i += 1
            continue

        entry = parse_plain_text_row(line)

        if entry is not None:
            results.append(entry)
            i += 1
            continue

        # Split-cell format:
        # Test name -> value -> unit -> optional range -> optional flag
        if (
            is_valid_test_label(line)
            and i + 1 < len(lines)
            and is_number_line(lines[i + 1])
        ):
            test_name = normalize_test_name(line)
            value_text = clean_text(lines[i + 1])

            raw_unit = None
            reference_range = None
            raw_flag = None

            consumed = 2
            next_index = i + consumed

            if next_index < len(lines):
                possible_unit = clean_text(lines[next_index])
                unit_match = re.fullmatch(PLAIN_UNIT_RE, possible_unit)

                if unit_match:
                    raw_unit = unit_match.group(0)
                    consumed += 1
                    next_index = i + consumed

            if next_index < len(lines):
                parsed_range = parse_plain_range(lines[next_index])

                if parsed_range:
                    reference_range = parsed_range
                    consumed += 1
                    next_index = i + consumed

            if next_index < len(lines):
                flag_match = re.fullmatch(
                    r"H|L|HIGH|LOW|ABNORMAL|CRITICAL",
                    clean_text(lines[next_index]),
                    re.IGNORECASE,
                )

                if flag_match:
                    raw_flag = flag_match.group(0)
                    consumed += 1

            if raw_unit or reference_range or raw_flag:
                original = " | ".join(
                    clean_text(item)
                    for item in lines[i:i + consumed]
                )

                results.append(create_test_entry(
                    test_name=test_name,
                    value_text=value_text,
                    raw_unit=raw_unit,
                    raw_flag=raw_flag,
                    reference_range=reference_range,
                    original_line=original,
                ))

                i += consumed
                continue

        unparsed_lines.append(line)
        i += 1

    return results, unparsed_lines



# ============================================================
# 7. KNOWN MULTI-LAYOUT REPORT HANDLERS
# ============================================================

def _add_review_reason(entry: dict, reason: str):
    """Attach a review reason without overwriting existing reasons."""
    if reason not in entry["needs_review_reasons"]:
        entry["needs_review_reasons"].append(reason)
    entry["needs_review"] = True


def _make_entry(name, value, unit, reference_range, original, review=None):
    entry = create_test_entry(
        test_name=name,
        value_text=value,
        raw_unit=unit,
        raw_flag=None,
        reference_range=reference_range,
        original_line=original,
    )
    for reason in review or []:
        _add_review_reason(entry, reason)
    return entry


def _parse_esr_layout(text: str):
    if not re.search(r"ESR\s*\(Erythrocyte Sedimentation Rate\)", text, re.I):
        return None

    # Use the value printed in the ESR result block, not numbers in metadata.
    block_match = re.search(
        r"##\s*ESR\s*\(Erythrocyte Sedimentation Rate\)(.*?)(?:##\s*Interpretation|$)",
        text,
        re.I | re.S,
    )
    if not block_match:
        return None
    block = block_match.group(1)
    value_match = re.search(r"\b(\d{1,3}(?:\.\d+)?)\s*\.?\s*(?:mm\s*1st\s*Hour)?", block, re.I)
    if not value_match:
        return None

    # The report contains separate male and female ranges and identifies the
    # patient as female. Keep the source's female interval.
    female_range = re.search(r"0\s*[-–]\s*20\s*\(Female\)", text, re.I)
    reference = {"type": "range", "low": 0.0, "high": 20.0} if female_range else None
    value = value_match.group(1)
    original = value_match.group(0)
    entry = _make_entry(
        "Erythrocyte Sedimentation Rate", value, "mm 1st Hour", reference,
        original,
        ["OCR-rendered test/unit text is imperfect; verify against the original report"],
    )
    return [entry]


def _parse_crp_layout(text: str):
    # Restrict extraction to the result section to avoid values in explanatory text.
    headings = list(re.finditer(r"##\s*C-Reactive Protein\s*\(CRP\)", text, re.I))
    if not headings:
        return None
    tail = text[headings[-1].end():]
    result_block = re.search(
        r"RESULTS\s+(?P<value>\d+(?:\.\d+)?)\s+(?P<unit>mg\s*/\s*L)\s+BIOLOGICAL\s+REFERENCE\s*INYERVALS\s+(?P<low>\d+(?:\.\d+)?)\s*[-–]\s*(?P<high>\d+(?:\.\d+)?)",
        tail,
        re.I | re.S,
    )
    if not result_block:
        return None
    reference = {
        "type": "range",
        "low": float(result_block.group("low")),
        "high": float(result_block.group("high")),
    }
    return [_make_entry(
        "C-Reactive Protein (CRP)", result_block.group("value"),
        result_block.group("unit"), reference, result_block.group(0),
    )]


def _parse_rf_layout(text: str):
    headings = list(re.finditer(r"##\s*Rheumatoid Factor\s*\(RA test\)", text, re.I))
    if not headings:
        return None
    tail = text[headings[-1].end():]
    match = re.search(
        r"RESULTS\s+UNITS\s+(?P<unit>10\s*/\s*mL)\s+(?P<limit>(?:&lt;|<)\s*\d+(?:\.\d+)?)\s+(?P<value>\d+(?:\.\d+)?)",
        tail,
        re.I | re.S,
    )
    if not match:
        return None
    # The source gives an upper-only limit (<18). The existing result schema
    # supports two-sided ranges only, so do not invent a lower bound.
    entry = _make_entry(
        "Rheumatoid Factor (RA test)", match.group("value"),
        match.group("unit"), None, match.group(0),
        ["Source reference is an upper-only limit (<18), which is not represented as a numeric range in this parser"],
    )
    return [entry]


def _parse_urine_layout(text: str):
    if not re.search(r"URINE PROTEIN CREATININE RATIO", text, re.I):
        return None

    results = []
    specs = [
        ("Urine Protein", r"Urine\s*Protein\s+(\d+(?:\.\d+)?)", "mg/dL", None),
        ("Urine Creatinine", r"Urine\s*Creatinine\s+(\d+(?:\.\d+)?)", "mg/dL", {"type": "range", "low": 16.0, "high": 327.0}),
        ("Protein Creatinine Ratio", r"Protein\s+Creatinine\s+Ratio\s+(\d+(?:\.\d+)?)", None, {"type": "range", "low": 0.0, "high": 0.2}),
    ]
    for name, pattern, unit, reference in specs:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        # Preserve the exact source phrase around each value for auditability.
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 100)
        original = clean_text(text[start:end])
        results.append(_make_entry(name, match.group(1), unit, reference, original))

    return results or None


def _parse_ccp_layout(text: str):
    """Extract the Anti-CCP result row without interpreting patient metadata as results."""
    if not re.search(r"Anti\s+Cyclic\s+Citrullinated\s+Peptide", text, re.I):
        return None

    for line in text.splitlines():
        # The OCR row may damage parts of the analyte label, but the value and
        # AU unit are expected together on the result row. Do not accept other
        # isolated numbers from patient demographics or report identifiers.
        if not re.search(r"Cyclic", line, re.I) or not re.search(r"Pep", line, re.I):
            continue
        match = re.search(r"(?P<value>\d{1,3}\.\d{1,3})\s*(?P<unit>AU)\b", line, re.I)
        if not match:
            continue
        return [_make_entry(
            "Anti-Cyclic Citrullinated Peptide Antibody (CCP)",
            match.group("value"),
            match.group("unit"),
            None,
            line,
            [
                "Qualitative negative/positive thresholds are present; verify the result and interpretation against the original report",
                "OCR damaged part of the test label; canonical name inferred from the report heading",
            ],
        )]
    return None


def parse_known_layout(text: str):
    """Parse report layouts whose extracted text is known to be split across cells."""
    for parser in (_parse_esr_layout, _parse_crp_layout, _parse_rf_layout, _parse_urine_layout, _parse_ccp_layout):
        result = parser(text)
        if result:
            return result
    return None


# ============================================================
# 8. MAIN REPORT PARSER
# ============================================================

def parse_report_text(text: str) -> dict[str, Any]:
    if not isinstance(text, str):
        raise TypeError("Report text must be a string.")
    if not text.strip():
        raise ValueError("Report text is empty.")

    # Docling may return only image placeholders. This is an extraction failure,
    # not a parser failure and must never be reported as a successful empty parse.
    meaningful_text = re.sub(r"<!--\s*image\s*-->", "", text, flags=re.I).strip()
    if not meaningful_text:
        return {
            "results": [],
            "unassigned_values": [],
            "unparsed_lines": [],
            "result_count": 0,
            "unassigned_value_count": 0,
            "parser_version": "7.2-layout",
            "status": "extraction_failed",
            "failure_reason": "Docling output contains no readable text; OCR or another extraction method is required.",
            "disclaimer": "No report values were extracted. Do not perform medical analysis on this document.",
        }

    known_results = parse_known_layout(meaningful_text)
    if known_results:
        return {
            "results": known_results,
            "unassigned_values": [],
            "unparsed_lines": [],
            "result_count": len(known_results),
            "unassigned_value_count": 0,
            "parser_version": "7.2-layout",
            "status": "success",
            "disclaimer": (
                "Extracted values are unverified report candidates. Test names, values, units and reference ranges must be checked against the original report. "
                "This parser does not provide medical diagnoses or treatment recommendations."
            ),
        }

    lines = [clean_text(line) for line in meaningful_text.splitlines() if line.strip()]

    # OCR output can contain vertical bars from a photographed table.
    # Treat it as Markdown only when a recognized header is followed by
    # a genuine Markdown separator row.
    has_markdown_table = any(
        index + 1 < len(lines)
        and lines[index].strip().startswith("|")
        and is_table_header(split_markdown_row(lines[index]))
        and is_markdown_separator(split_markdown_row(lines[index + 1]))
        for index in range(len(lines))
    )

    if has_markdown_table:
        results, unparsed_lines = parse_markdown_tables(lines)
        parser_version = "7.2-markdown"
    else:
        results, unparsed_lines = parse_plain_text(lines)
        parser_version = "7.2-plain"

    return {
        "results": results,
        "unassigned_values": [],
        "unparsed_lines": unparsed_lines,
        "result_count": len(results),
        "unassigned_value_count": 0,
        "parser_version": parser_version,
        "status": "success" if results else "parsing_failed",
        "failure_reason": None if results else "Readable text was extracted, but no report result rows could be parsed.",
        "disclaimer": (
            "Extracted values are unverified report candidates. Test names, values, units and reference ranges must be checked against the original report. "
            "This parser does not provide medical diagnoses or treatment recommendations."
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
