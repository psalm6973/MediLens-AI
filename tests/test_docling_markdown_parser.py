
from utils.report_parser import parse_report_text


REPORT_TABLE = """
| Test                         | Test                         | Test         |   Result | Units   | Status   | Reference Range   |        |
|------------------------------|------------------------------|--------------|----------|---------|----------|-------------------|--------|
| Total Protein                | Total Protein                | Conventional |     6.80 | IP/8    |          | 6.70              |   8.20 |
| Serum                        | Biuret                       | S.I.         |    68.00 | 1/6     |          | 67.00             |  82.00 |
| Albumin                      | Albumin                      | Conventional |     2.80 | IP/6    | L        | 3.50              |   5.00 |
| Serum                        | Bromocresol Purple           | S.I.         |    28.00 | 1/6     |          | 35.00             |  50.00 |
| Globulin(calculated)         | Globulin(calculated)         | Conventional |     4.00 | IP/6    |          | 2.60              |   4.10 |
| Serum                        | Serum                        | S.1.         |    40.00 | g/l     |          | 26.00             |  41.00 |
| A/G Ratio (calculated) Serum | A/G Ratio (calculated) Serum |              |     0.70 |         | L        | 1.20              |   2.50 |
| Bilirubin(Total)             | Bilirubin(Total)             | Conventional |     0.80 | mdl     |          | 0.20              |   1.00 |
| Serum                        | Diazo                        | S.I.         |    13.68 | umol/l  |          | 3.42              |  17.10 |
| SGOT                         |                              | Conventional |    38.00 | U/I     | H        | 9.00              |  36.00 |
| Serum                        | Enzymatic                    | S.I.         |    38.00 | IU/     |          | 9.00              |  36.00 |
| SGPT                         |                              | Conventional |    76.00 | U/I     | H        | 10.00-            |  40.00 |
| Serum                        | Enzymatic                    | S.I.         |    76.00 | 1U/I    |          | 10.00             |  40.00 |
| Alkaline Phosphatase         | Alkaline Phosphatase         | Conventional |   128.00 | v/n     | H        | 40.00-            |  120.0 |
| Serum                        | Enzymatic                    | S.I.         |   128.00 | 1U/I    |          | 40.00             | 120.00 |
"""


def test_report4_markdown_parser():

    report = parse_report_text(REPORT_TABLE)

    # Check total number of primary tests.
    assert report["result_count"] == 8

    # Check test names.
    names = [
        item["test_name"]
        for item in report["results"]
    ]

    assert names == [
        "Total Protein",
        "Albumin",
        "Globulin",
        "A/G Ratio",
        "Total Bilirubin",
        "SGOT",
        "SGPT",
        "Alkaline Phosphatase",
    ]

    # Check primary result values.
    expected_values = [
        6.80,
        2.80,
        4.00,
        0.70,
        0.80,
        38.00,
        76.00,
        128.00,
    ]

    actual_values = [
        item["value"]
        for item in report["results"]
    ]

    assert actual_values == expected_values

    # Check alternate S.I. values.
    alternate_counts = [
        len(item["alternate_values"])
        for item in report["results"]
    ]

    assert alternate_counts == [
        1, 1, 1, 0, 1, 1, 1, 1
    ]

    expected_alternates = [
        68.00,
        28.00,
        40.00,
        None,
        13.68,
        38.00,
        76.00,
        128.00,
    ]

    for index, expected in enumerate(expected_alternates):

        alternates = report["results"][index]["alternate_values"]

        if expected is None:
            assert len(alternates) == 0
        else:
            assert alternates[0]["value"] == expected

    # Unknown OCR units must be preserved and flagged for review.
    assert report["results"][0]["raw_ocr_unit"] == "IP/8"
    assert report["results"][0]["needs_review"] is True

    # Display parser results.
    print("\nParser version:", report["parser_version"])
    print("Total primary tests:", report["result_count"])

    for item in report["results"]:

        print("\nTest:", item["test_name"])
        print("Primary value:", item["value"])
        print("Unit:", item["raw_ocr_unit"])
        print("Alternate values:", item["alternate_values"])
        print("Reference:", item["reference_range"])
        print("Flag:", item["flag"])
        print("Needs review:", item["needs_review"])

    print("\nAll Report 4 parser checks passed!")
