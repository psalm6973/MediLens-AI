from pathlib import Path
import json
import logging

from docling.document_converter import DocumentConverter


logger = logging.getLogger(__name__)


def _save_debug_files(result, markdown: str, source_path: Path) -> None:
    """
    Save Docling's original extraction output for inspection.

    These exports do not modify the extracted content.
    """
    debug_dir = Path("data/docling_debug") / source_path.stem
    debug_dir.mkdir(parents=True, exist_ok=True)

    # Save Markdown
    (debug_dir / "document.md").write_text(
        markdown,
        encoding="utf-8"
    )

    # Save the complete Docling document structure
    try:
        document_data = result.document.export_to_dict()

        with (debug_dir / "document.json").open(
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                document_data,
                file,
                indent=2,
                ensure_ascii=False,
                default=str
            )

    except Exception as error:
        logger.warning("Could not export Docling JSON: %s", error)

    # Save extracted tables
    tables = getattr(result.document, "tables", [])

    table_summary = [
        f"Source: {source_path.name}",
        f"Number of tables: {len(tables)}",
        ""
    ]

    for index, table in enumerate(tables, start=1):
        try:
            dataframe = table.export_to_dataframe(
                doc=result.document
            )

            csv_path = debug_dir / f"table_{index:02d}.csv"
            dataframe.to_csv(csv_path, index=False)

            table_summary.extend([
                f"Table {index}",
                f"Rows: {len(dataframe)}",
                f"Columns: {len(dataframe.columns)}",
                f"CSV: {csv_path.name}",
                ""
            ])

            # HTML is optional; failure must not affect extraction.
            try:
                html = table.export_to_html(doc=result.document)

                (debug_dir / f"table_{index:02d}.html").write_text(
                    html,
                    encoding="utf-8"
                )
            except Exception as error:
                logger.warning(
                    "Could not export HTML for table %s: %s",
                    index,
                    error
                )

        except Exception as error:
            table_summary.extend([
                f"Table {index}: export failed",
                str(error),
                ""
            ])

    (debug_dir / "table_summary.txt").write_text(
        "\n".join(table_summary),
        encoding="utf-8"
    )

    logger.info("Docling debug files saved to: %s", debug_dir)


def extract_with_docling(
    file_path: str | Path,
    save_debug: bool = False
) -> str:
    """
    Extract document content using Docling's default processing pipeline.

    Important:
    - Uses DocumentConverter defaults.
    - Does not force Tesseract or a custom OCR configuration.
    - Does not apply report-specific corrections.
    - Does not modify extracted values.
    """

    source_path = Path(file_path)

    if not source_path.exists():
        raise FileNotFoundError(
            f"Document not found: {source_path}"
        )

    if not source_path.is_file():
        raise ValueError(
            f"Expected a file, received: {source_path}"
        )

    logger.info("Starting Docling extraction: %s", source_path)

    # Keep Docling's default OCR, layout and table-processing settings.
    converter = DocumentConverter()

    result = converter.convert(str(source_path))

    markdown = result.document.export_to_markdown()

    if markdown is None:
        markdown = ""

    if save_debug:
        try:
            _save_debug_files(
                result=result,
                markdown=markdown,
                source_path=source_path
            )
        except Exception:
            # Debug-export failures must not destroy a successful extraction.
            logger.exception("Could not save Docling debug files.")

    logger.info(
        "Docling extraction completed. Characters: %s",
        len(markdown)
    )

    return markdown