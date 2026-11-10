from __future__ import annotations

import time
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableFormerMode,
    TesseractCliOcrOptions,
)
from docling.document_converter import DocumentConverter, ImageFormatOption


INPUT_FILE = Path("data/datasets/ekacare/images/report_004.png")
OUTPUT_DIR = Path("data/docling_debug/report_004_tesseract")
TESSERACT_EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def main() -> None:
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(f"Report image not found: {INPUT_FILE.resolve()}")

    if not TESSERACT_EXE.is_file():
        raise FileNotFoundError(
            "Tesseract executable not found at: "
            f"{TESSERACT_EXE}. Update TESSERACT_EXE in this test file."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Keep Docling's layout and table-structure stages. Only change the OCR
    # engine used inside the Docling pipeline for this comparison run.
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    pipeline_options.table_structure_options.do_cell_matching = True
    pipeline_options.ocr_options = TesseractCliOcrOptions(
        tesseract_cmd=str(TESSERACT_EXE),
        lang=["eng"],
        psm=6,
    )

    converter = DocumentConverter(
        format_options={
            InputFormat.IMAGE: ImageFormatOption(
                pipeline_options=pipeline_options
            )
        }
    )

    print(f"Input: {INPUT_FILE}")
    print("Docling OCR engine: Tesseract CLI (PSM 6)")
    print("Starting conversion...")
    start = time.perf_counter()

    result = converter.convert(str(INPUT_FILE))
    document = result.document
    elapsed = time.perf_counter() - start

    markdown = document.export_to_markdown()
    (OUTPUT_DIR / "document.md").write_text(markdown, encoding="utf-8")

    tables = getattr(document, "tables", []) or []
    summary = [
        f"Input: {INPUT_FILE}",
        "OCR engine: Tesseract CLI (PSM 6)",
        f"Elapsed seconds: {elapsed:.2f}",
        f"Detected tables: {len(tables)}",
        "",
    ]

    for index, table in enumerate(tables, start=1):
        dataframe = table.export_to_dataframe(doc=document)
        number = f"{index:02d}"
        dataframe.to_csv(
            OUTPUT_DIR / f"table_{number}.csv",
            index=False,
            encoding="utf-8-sig",
        )
        (OUTPUT_DIR / f"table_{number}.html").write_text(
            table.export_to_html(doc=document),
            encoding="utf-8",
        )
        summary.extend(
            [
                f"TABLE {index}",
                f"Shape: {dataframe.shape[0]} rows x {dataframe.shape[1]} columns",
                f"Columns: {list(dataframe.columns)}",
                dataframe.to_string(index=False),
                "",
            ]
        )

    (OUTPUT_DIR / "table_summary.txt").write_text(
        "\n".join(summary), encoding="utf-8"
    )

    print(f"\nConversion completed in {elapsed:.2f} seconds.")
    print(f"Detected tables: {len(tables)}")
    print(f"Debug output: {OUTPUT_DIR}")
    print("\n========== MARKDOWN OUTPUT ==========\n")
    print(markdown)
    print("\n========== TABLE SUMMARY ==========\n")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
