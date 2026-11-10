
from utils.report_parser import parse_report_text


def test_ocr_confusable_units_are_normalized_but_flagged():
    markdown = """
| Test | Result | Units | Reference Range |
|---|---:|---|---|
| Total Protein | 6.20 | 7p/6 | 6.6 - 8.3 |
| Globulin conventional | 4.00 | IP/8 | 2.6 - 4.1 |
| Albumin | 2.80 | IP/6 | 3.5 - 5.0 |
| Globulin | 4.00 | 1/6 | 26 - 41 |
| Bilirubin | 1.26 | mdl | 0.3 - 1.2 |
| Direct Bilirubin | 0.29 | m/dl | 0.0 - 0.2 |
| SGOT | 32 | U/I | <50 |
| SGPT | 40 | IU/ | <35 |
"""
    report = parse_report_text(markdown)
    results = report["results"]

    # Use raw OCR units to distinguish duplicate normalized test names.
    rows_by_raw_unit = {
        item["raw_ocr_unit"]: item for item in results
    }

    assert rows_by_raw_unit["7p/6"]["test_name"] == "Total Protein"
    assert rows_by_raw_unit["7p/6"]["unit"] == "g/dL"
    assert rows_by_raw_unit["7p/6"]["needs_review"] is True

    assert rows_by_raw_unit["IP/8"]["test_name"] == "Globulin"
    assert rows_by_raw_unit["IP/8"]["unit"] == "g/dL"
    assert rows_by_raw_unit["IP/8"]["needs_review"] is True

    assert rows_by_raw_unit["IP/6"]["unit"] == "g/dL"
    assert rows_by_raw_unit["IP/6"]["needs_review"] is True

    assert rows_by_raw_unit["1/6"]["test_name"] == "Globulin"
    assert rows_by_raw_unit["1/6"]["unit"] == "g/L"
    assert rows_by_raw_unit["1/6"]["needs_review"] is True

    assert rows_by_raw_unit["mdl"]["unit"] == "mg/dL"
    assert rows_by_raw_unit["mdl"]["needs_review"] is True

    assert rows_by_raw_unit["m/dl"]["unit"] == "mg/dL"
    assert rows_by_raw_unit["m/dl"]["needs_review"] is True

    assert rows_by_raw_unit["U/I"]["unit"] == "U/L"
    assert rows_by_raw_unit["U/I"]["needs_review"] is True

    assert rows_by_raw_unit["IU/"]["unit"] == "IU/L"
    assert rows_by_raw_unit["IU/"]["needs_review"] is True


def test_upper_and_lower_only_reference_limits_are_preserved():
    markdown = """
| Test | Result | Units | Reference Range |
|---|---:|---|---|
| AST | 32 | U/L | <50 |
| ALT | 40 | U/L | <35 |
| Marker A | 12 | mg/L | >10 |
| Marker B | 10 | mg/L | >=10 |
"""
    report = parse_report_text(markdown)
    results = {
        item["test_name"]: item for item in report["results"]
    }

    assert results["AST"]["reference_range"] == {
        "type": "upper_limit",
        "operator": "<",
        "value": 50.0
    }
    assert results["AST"]["reference_status"] == "within"
    assert results["ALT"]["reference_status"] == "above"

    assert results["Marker A"]["reference_range"] == {
        "type": "lower_limit",
        "operator": ">",
        "value": 10.0
    }
    assert results["Marker A"]["reference_status"] == "within"
    assert results["Marker B"]["reference_status"] == "within"


def test_two_sided_reference_ranges_remain_unchanged():
    markdown = """
| Test | Result | Units | Reference Range |
|---|---:|---|---|
| Total Protein | 6.8 | g/dL | 6.7 - 8.2 |
"""
    report = parse_report_text(markdown)
    item = report["results"][0]

    assert item["reference_range"] == {
        "type": "range",
        "low": 6.7,
        "high": 8.2
    }
    assert item["reference_status"] == "within"


def test_reference_intervals_are_formatted_for_result_page():
    from agents.medical_analysis import prepare_display_fields

    analysis = {
        "findings": [
            {
                "test_name": "SGOT",
                "meaning": "Enzyme test",
                "observation": "Review"
            },
            {
                "test_name": "Total Protein",
                "meaning": "Protein test",
                "observation": "Review"
            },
        ]
    }

    results = [
        {
            "test_name": "SGOT",
            "unit": "U/L",
            "reference_range": {
                "type": "upper_limit",
                "operator": "<",
                "value": 50.0
            },
        },
        {
            "test_name": "Total Protein",
            "unit": "g/dL",
            "reference_range": {
                "type": "range",
                "low": 6.7,
                "high": 8.2
            },
        },
    ]

    prepare_display_fields(analysis, results)

    assert analysis["findings"][0]["reference_range"] == "<50 U/L"
    assert analysis["findings"][1]["reference_range"] == "6.7 - 8.2 g/dL"
