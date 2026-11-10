"""
MediLens-AI Docling document extraction.

Primary extraction uses Docling's table/layout pipeline with Tesseract CLI
as Docling's internal OCR engine. This is NOT the separate external OCR
fallback; it keeps extraction and table reconstruction inside Docling.

Public interface:
    extract_with_docling(file_path, save_debug=False) -> str
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableStructureOptions,
    TesseractCliOcrOptions,
)
from docling.document_converter import (
    DocumentConverter,
    ImageFormatOption,
    PdfFormatOption,
)

logger = logging.getLogger(__name__)


def _find_tesseract() -> str:
    """Find Tesseract, including the common Windows installation path."""
    configured = os.getenv("TESSERACT_CMD")
    if configured and Path(configured).is_file():
        return configured

    from_path = shutil.which("tesseract")
    if from_path:
        return from_path

    common_windows_path = Path(
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )
    if common_windows_path.is_file():
        return str(common_windows_path)

    # Let Docling/Tesseract produce a clear error if it is not installed.
    return "tesseract"


@lru_cache(maxsize=1)
def get_converter() -> DocumentConverter:
    """
    Create and cache one Docling converter.

    PSM 6 is selected because the reports in this dataset are mostly
    structured laboratory-report pages with aligned text and tables.
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=True
    )
    pipeline_options.ocr_options = TesseractCliOcrOptions(
        lang=["eng"],
        psm=6,
        tesseract_cmd=_find_tesseract(),
    )

    # Keep one options object for both scanned PDFs and standalone images.
    # ImageFormatOption uses Docling's standard layout/table pipeline too.
    return DocumentConverter(
        format_options={
            InputFormat.IMAGE: ImageFormatOption(
                pipeline_options=pipeline_options
            ),
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options
            ),
        }
    )


def _save_debug_files(result: Any, markdown: str, source_path: Path) -> Path:
    """Save useful Docling outputs without changing the returned Markdown."""
    debug_dir = Path("data") / "docling_debug" / source_path.stem
    debug_dir.mkdir(parents=True, exist_ok=True)

    (debug_dir / "document.md").write_text(markdown, encoding="utf-8")

    try:
        document_dict = result.document.export_to_dict()
        (debug_dir / "document.json").write_text(
            json.dumps(document_dict, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        logger.exception("Could not save Docling JSON debug export.")

    table_summaries: list[str] = []
    for index, table in enumerate(
        getattr(result.document, "tables", []) or [], start=1
    ):
        try:
            dataframe = table.export_to_dataframe(doc=result.document)
            csv_path = debug_dir / f"table_{index:02d}.csv"
            dataframe.to_csv(csv_path, index=False, encoding="utf-8-sig")

            html_path = debug_dir / f"table_{index:02d}.html"
            html_path.write_text(
                dataframe.to_html(index=False),
                encoding="utf-8",
            )

            table_summaries.append(
                f"TABLE {index}\n"
                f"Shape: {dataframe.shape[0]} rows x "
                f"{dataframe.shape[1]} columns\n"
                f"Columns: {list(dataframe.columns)}"
            )
        except Exception as error:
            table_summaries.append(
                f"TABLE {index}\nCould not export table: {error}"
            )

    summary = (
        f"Source: {source_path}\n"
        f"Detected tables: {len(getattr(result.document, 'tables', []) or [])}\n\n"
        + ("\n\n".join(table_summaries) if table_summaries else "No tables detected.")
    )
    (debug_dir / "table_summary.txt").write_text(
        summary,
        encoding="utf-8",
    )
    return debug_dir


def extract_with_docling(
    file_path: str | Path,
    save_debug: bool = False,
) -> str:
    """
    Extract structured text and tables from a report using Docling.

    Args:
        file_path: Path to a PDF or image report.
        save_debug: When True, save Markdown, JSON, CSV/HTML tables,
                    and a table summary under data/docling_debug/<filename>/.

    Returns:
        Extracted document content in Markdown format.

    Raises:
        FileNotFoundError: If the report does not exist.
        ValueError: If Docling produces empty content.
        RuntimeError: If document conversion fails.
    """
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"Report file not found: {path}")

    try:
        converter = get_converter()
        result = converter.convert(str(path))

        extracted_text = result.document.export_to_markdown()

        if not extracted_text or not extracted_text.strip():
            raise ValueError(
                "Docling could not extract readable content. "
                "The report may require the separate OCR fallback."
            )

        extracted_text = extracted_text.strip()

        if save_debug:
            debug_dir = _save_debug_files(result, extracted_text, path)
            logger.info("Docling debug files saved to: %s", debug_dir)

        return extracted_text

    except ValueError:
        raise
    except Exception as error:
        logger.exception("Docling extraction failed for %s", path)
        raise RuntimeError(
            f"Docling extraction failed: {error}"
        ) from error
