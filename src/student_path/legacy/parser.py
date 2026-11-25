"""
LEGACY v1 parser (superseded, see student_path/legacy/__init__.py).

Parse the Modulkatalog PDF using Docling.

Converts the PDF into structured Markdown, preserving tables and headings,
and saves the raw Docling result for inspection before normalization.

Usage (see `uv run sp legacy parse --help`):
    uv run sp legacy parse
    uv run sp legacy parse --pdf path/to/other.pdf
    uv run sp legacy parse --pages 1-10    # first 10 pages only (for testing)
"""

import json
import os


def parse_pdf(pdf_path: str, output_dir: str, page_range: tuple[int, int] | None = None) -> str:
    """
    Parse a PDF using Docling and save the structured Markdown output.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save output files
        page_range: Optional (first, last) page numbers, 1-based and inclusive

    Returns:
        Path to the saved Markdown file
    """
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.base_models import InputFormat

    print(f"[1/4] Loading PDF: {pdf_path}")
    print(f"       File size: {os.path.getsize(pdf_path) / 1024 / 1024:.1f} MB")

    # Configure Docling pipeline for optimal table extraction
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True  # Enable OCR for scanned content
    pipeline_options.do_table_structure = True  # Preserve table structure

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    print("[2/4] Running Docling conversion (this may take several minutes for 600+ pages)...")

    # Convert the PDF (optionally only a page range)
    if page_range:
        print(f"       Pages: {page_range[0]}-{page_range[1]}")
        result = converter.convert(pdf_path, page_range=page_range)
    else:
        result = converter.convert(pdf_path)
    doc = result.document

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Export as Markdown
    md_output_path = os.path.join(output_dir, "modulkatalog_raw.md")
    markdown_content = doc.export_to_markdown()
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"[3/4] Saved Markdown output: {md_output_path}")
    print(f"       Size: {len(markdown_content) / 1024:.1f} KB, {markdown_content.count(chr(10))} lines")

    # Also export the structured document as JSON for deeper inspection
    json_output_path = os.path.join(output_dir, "modulkatalog_docling.json")
    doc_dict = doc.export_to_dict()
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(doc_dict, f, indent=2, ensure_ascii=False)
    print(f"[4/4] Saved structured JSON: {json_output_path}")

    # Print quick stats
    tables_found = sum(1 for item in doc.tables) if hasattr(doc, 'tables') else "unknown"
    print(f"\n--- Parsing Summary ---")
    print(f"  Tables detected: {tables_found}")
    print(f"  Markdown length: {len(markdown_content):,} characters")
    print(f"\nNext step: Inspect {md_output_path} to verify table extraction quality,")
    print("then run: uv run sp legacy normalize")

    return md_output_path


def quick_inspect(output_dir: str, num_samples: int = 3):
    """
    Quick inspection of the Docling output to verify quality.
    Prints the first few table-like sections found.
    """
    md_path = os.path.join(output_dir, "modulkatalog_raw.md")
    if not os.path.exists(md_path):
        print(f"No output found at {md_path}. Run parser first.")
        return

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find table blocks (lines starting with |)
    lines = content.split("\n")
    table_blocks = []
    current_block = []
    in_table = False

    for line in lines:
        if line.strip().startswith("|"):
            in_table = True
            current_block.append(line)
        else:
            if in_table and current_block:
                table_blocks.append("\n".join(current_block))
                current_block = []
            in_table = False

    if current_block:
        table_blocks.append("\n".join(current_block))

    print(f"\n=== Quick Inspection: Found {len(table_blocks)} table blocks ===\n")

    for i, block in enumerate(table_blocks[:num_samples]):
        print(f"--- Table Block {i+1} (first 20 lines) ---")
        block_lines = block.split("\n")
        for line in block_lines[:20]:
            print(line)
        if len(block_lines) > 20:
            print(f"  ... ({len(block_lines) - 20} more lines)")
        print()
