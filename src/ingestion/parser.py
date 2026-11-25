"""
Phase 1, Task 1.1-1.2: Parse the Modulkatalog PDF using Docling.

Converts the PDF into structured Markdown, preserving tables and headings.
Outputs the raw Docling result for inspection before normalization.

Usage:
    python src/ingestion/parser.py
    python src/ingestion/parser.py --pdf path/to/other.pdf
    python src/ingestion/parser.py --pages 0-10    # Parse only first 10 pages (for testing)
"""

import argparse
import os
import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_pdf(pdf_path: str, output_dir: str, page_range: str = None) -> str:
    """
    Parse a PDF using Docling and save the structured Markdown output.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save output files
        page_range: Optional page range like "0-10" (0-indexed)

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

    # Convert the PDF
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
    print(f"then run: python src/ingestion/normalizer.py")

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse Modulkatalog PDF using Docling"
    )
    parser.add_argument(
        "--pdf",
        default=str(PROJECT_ROOT / "Modulkatalog-Master-Informatik.pdf"),
        help="Path to the PDF file",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "data" / "raw"),
        help="Directory for output files",
    )
    parser.add_argument(
        "--pages",
        default=None,
        help="Page range to parse, e.g. '0-10' (0-indexed). Omit for full PDF.",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="After parsing, print sample table blocks for quick inspection",
    )

    args = parser.parse_args()

    # Parse the PDF
    md_path = parse_pdf(args.pdf, args.output_dir, args.pages)

    # Optional quick inspection
    if args.inspect:
        quick_inspect(args.output_dir)
