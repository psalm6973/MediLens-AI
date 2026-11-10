"""Layout-aware parsing for Docling Markdown tables.

This module deliberately keeps OCR text unchanged. It interprets table columns
from their headers and preserves uncertain units/values for human review.
"""

from __future__ import annotations

import re
from typing import Callable, Any

NUMBER = r"-?\d[\d,]*(?:\.\d+)?"
NUMBER_RE = re.compile(rf"^{NUMBER}$")
INLINE_NUMBER_RE = re.compile(rf"^\s*({NUMBER})(.*)$")
DATE_HEADER_RE = re.compile(
    r"\b\d{1,2}[/-][A-Za-z]{3}[/-]\d{2,4}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    re.IGNORECASE,
)


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _clean(value).lower())


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-{2,}:?", cell.replace(" ", ""))
        for cell in cells
    )


def _is_date_header(value: str) -> bool:
    return bool(DATE_HEADER_RE.search(_clean(value)))


def _build_schema(headers: list[str]) -> dict[str, Any] | None:
    """Infer a supported table layout from its header row."""
    if not headers:
        return None

    normalized = [_key(cell) for cell in headers]
    result_indices = [
        i for i, key in enumerate(normalized)
        if key in {"result", "results", "value", "reading", "observation"}
        or key.startswith("result")
    ]

    # Two or more RESULT columns indicate side-by-side panels. Each panel is
    # interpreted independently as [label, result], without mixing columns.
    if len(result_indices) >= 2:
        panels = [(i - 1, i) for i in result_indices if i > 0]
        if len(panels) >= 2:
            return {"kind": "panels", "panels": panels, "headers": headers}

    # Historical-result reports often label the first column "Date", while
    # the actual test names occupy that column and date headings follow it.
    date_indices = [i for i, cell in enumerate(headers) if _is_date_header(cell)]
    if (
        normalized[0] in {"date", "dates"}
        and len(date_indices) >= 2
    ):
        unit_idx = next(
            (i for i, key in enumerate(normalized) if "unit" in key), None
        )
        range_idx = next(
            (
                i for i, key in enumerate(normalized)
                if any(term in key for term in ("reference", "bioref", "normalrange", "biological"))
            ),
            None,
        )
        return {
            "kind": "historical",
            "name": 0,
            "value": date_indices[0],
            "historical": date_indices[1:],
            "unit": unit_idx,
            "flag": None,
            "range": range_idx,
            "range_upper": None,
            "headers": headers,
        }

    # Conventional laboratory tables: identify semantic columns rather than
    # assuming a fixed number or order of columns.
    name_indices = [
        i for i, key in enumerate(normalized)
        if (
            key in {"test", "testname", "analyte", "investigation", "parameter"}
            or key.endswith("testname")
        )
    ]
    value_idx = result_indices[0] if result_indices else None
    if value_idx is None:
        return None

    name_idx = name_indices[0] if name_indices else 0
    if name_idx >= value_idx:
        name_idx = 0

    unit_idx = next(
        (i for i, key in enumerate(normalized) if "unit" in key), None
    )
    flag_idx = next(
        (i for i, key in enumerate(normalized)
         if key in {"flag", "status", "remarks", "mark"}),
        None,
    )
    range_idx = next(
        (
            i for i, key in enumerate(normalized)
            if any(term in key for term in ("reference", "bioref", "normalrange", "biological"))
        ),
        None,
    )

    range_upper_idx = None
    if range_idx is not None:
        # Some PDF tables split a single reference interval over two cells:
        # the first cell is headed "Reference Range" and the adjacent cell
        # has a blank header containing the upper limit.
        if range_idx + 1 < len(headers):
            next_key = normalized[range_idx + 1]
            if not next_key or next_key in {"high", "upper", "maximum", "max"}:
                range_upper_idx = range_idx + 1

    # Repeated "Test" headings commonly represent test name, method, and
    # measurement type. The last such column before Result identifies the
    # Conventional/S.I. row marker; this is a generic paired-row convention.
    variant_idx = None
    if len(name_indices) >= 2:
        earlier_test_columns = [i for i in name_indices if i < value_idx]
        if len(earlier_test_columns) >= 2:
            variant_idx = earlier_test_columns[-1]

    if not any([name_idx is not None, value_idx is not None]):
        return None

    return {
        "kind": "standard",
        "name": name_idx,
        "value": value_idx,
        "unit": unit_idx,
        "flag": flag_idx,
        "range": range_idx,
        "range_upper": range_upper_idx,
        "variant": variant_idx,
        "headers": headers,
    }


def _cell(cells: list[str], index: int | None) -> str:
    if index is None or index < 0 or index >= len(cells):
        return ""
    return _clean(cells[index])


def _parse_range(
    cells: list[str],
    schema: dict[str, Any],
    parse_range_parts: Callable,
    parse_plain_range: Callable,
):
    range_idx = schema.get("range")
    if range_idx is None:
        return None, ""

    raw_range = _cell(cells, range_idx)
    upper_idx = schema.get("range_upper")
    if upper_idx is not None:
        low = _cell(cells, range_idx)
        high = _cell(cells, upper_idx)
        parsed = parse_range_parts(low, high) if low and high else None
        return parsed, " ".join(part for part in (low, high) if part)

    return parse_plain_range(raw_range), raw_range


def _numeric_value_and_inline_unit(value: str):
    """Read a scalar numeric result and optional attached unit, never ratios."""
    match = INLINE_NUMBER_RE.fullmatch(_clean(value))
    if not match:
        return None, None

    numeric_text = match.group(1)
    suffix = _clean(match.group(2))

    # A value such as 6/6 or 120/80 is a ratio/vital-sign pair, not one scalar
    # laboratory result. Do not silently take the first number.
    if suffix.startswith("/"):
        return None, None

    if not NUMBER_RE.fullmatch(numeric_text):
        return None, None

    return numeric_text, suffix or None


def _make_primary(
    cells: list[str],
    schema: dict[str, Any],
    original_line: str,
    callbacks: dict[str, Callable],
):
    name = _cell(cells, schema.get("name"))
    value_text = _cell(cells, schema.get("value"))

    if not callbacks["is_valid_test_label"](name):
        return None
    if not NUMBER_RE.fullmatch(value_text.replace(",", "")):
        return None

    raw_unit = _cell(cells, schema.get("unit")) or None
    raw_flag = _cell(cells, schema.get("flag")) or None
    reference_range, raw_range = _parse_range(
        cells,
        schema,
        callbacks["parse_range_parts"],
        callbacks["parse_plain_range"],
    )

    reasons = []
    if raw_range and not reference_range:
        reasons.append(
            "Reference interval could not be parsed; verify the original report"
        )

    entry = callbacks["create_test_entry"](
        test_name=callbacks["normalize_test_name"](name),
        value_text=value_text,
        raw_unit=raw_unit,
        raw_flag=raw_flag,
        reference_range=reference_range,
        original_line=original_line,
        extra_review_reasons=reasons,
    )

    if schema.get("kind") == "historical":
        history = []
        for index in schema.get("historical", []):
            historical_text = _cell(cells, index)
            if NUMBER_RE.fullmatch(historical_text.replace(",", "")):
                history.append({
                    "date": schema["headers"][index],
                    "value": float(historical_text.replace(",", "")),
                })
        entry["historical_values"] = history

    return entry


def _parse_panel_rows(
    cells: list[str],
    schema: dict[str, Any],
    original_line: str,
    callbacks: dict[str, Callable],
):
    parsed = []
    for name_idx, value_idx in schema["panels"]:
        name = _cell(cells, name_idx)
        value_cell = _cell(cells, value_idx)
        if not callbacks["is_valid_test_label"](name):
            continue

        value_text, inline_unit = _numeric_value_and_inline_unit(value_cell)
        if value_text is None:
            continue

        reasons = []
        if not inline_unit:
            reasons.append(
                "Unit was not present alongside this numeric result; verify the original report"
            )

        parsed.append({
            "row_type": "primary",
            "entry": callbacks["create_test_entry"](
                test_name=callbacks["normalize_test_name"](name),
                value_text=value_text,
                raw_unit=inline_unit,
                raw_flag=None,
                reference_range=None,
                original_line=original_line,
                extra_review_reasons=reasons,
            ),
        })
    return parsed


def _split_row(line: str) -> list[str]:
    text = line.strip()
    if not text.startswith("|"):
        return []
    if text.endswith("|"):
        text = text[1:-1]
    else:
        text = text[1:]
    return [_clean(cell) for cell in text.split("|")]


def parse_docling_table_text(
    text: str,
    *,
    create_test_entry: Callable,
    normalize_test_name: Callable,
    parse_range_parts: Callable,
    parse_plain_range: Callable,
    attach_alternate_value: Callable,
    is_si_marker: Callable,
    is_valid_test_label: Callable,
):
    """Return ``(results, unparsed_lines)`` if a supported table is present.

    Return ``None`` when no supported Markdown table header is found, allowing
    the existing plain-text/legacy parser to handle the document.
    """
    callbacks = {
        "create_test_entry": create_test_entry,
        "normalize_test_name": normalize_test_name,
        "parse_range_parts": parse_range_parts,
        "parse_plain_range": parse_plain_range,
        "attach_alternate_value": attach_alternate_value,
        "is_si_marker": is_si_marker,
        "is_valid_test_label": is_valid_test_label,
    }

    results: list[dict] = []
    unparsed_lines: list[str] = []
    schema = None
    table_result_start = 0
    recognized_table = False

    for line in text.splitlines():
        if not line.strip().startswith("|"):
            schema = None
            continue

        cells = _split_row(line)
        if not cells or _is_separator(cells):
            continue

        candidate_schema = _build_schema(cells)
        if candidate_schema is not None:
            schema = candidate_schema
            table_result_start = len(results)
            recognized_table = True
            continue

        if schema is None:
            continue

        if schema["kind"] == "panels":
            for item in _parse_panel_rows(cells, schema, line, callbacks):
                results.append(item["entry"])
            continue

        # Conventional/S.I. paired rows: only attach an S.I. row when the row
        # label is Serum/Plasma and the measurement-type cell identifies S.I.
        variant_idx = schema.get("variant")
        row_name = _cell(cells, schema.get("name"))
        variant = _cell(cells, variant_idx)
        if (
            variant_idx is not None
            and row_name.lower() in {"serum", "plasma"}
            and callbacks["is_si_marker"](variant)
        ):
            value_text = _cell(cells, schema.get("value"))
            if NUMBER_RE.fullmatch(value_text.replace(",", "")) and len(results) > table_result_start:
                raw_unit = _cell(cells, schema.get("unit")) or None
                raw_flag = _cell(cells, schema.get("flag")) or None
                reference_range, _ = _parse_range(
                    cells,
                    schema,
                    callbacks["parse_range_parts"],
                    callbacks["parse_plain_range"],
                )
                alternate = callbacks["create_test_entry"](
                    test_name=results[-1]["test_name"],
                    value_text=value_text,
                    raw_unit=raw_unit,
                    raw_flag=raw_flag,
                    reference_range=reference_range,
                    original_line=line,
                )
                callbacks["attach_alternate_value"](results[-1], alternate)
            else:
                unparsed_lines.append(line)
            continue

        entry = _make_primary(cells, schema, line, callbacks)
        if entry is not None:
            results.append(entry)
        elif any(cells):
            unparsed_lines.append(line)

    if not recognized_table:
        return None

    return results, unparsed_lines
