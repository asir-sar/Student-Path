"""P1.2: run Docling once on the catalogue and cache the DoclingDocument JSON.

Configuration follows findings F1/F7 in context/IMPLEMENTATION_PLAN.md:
- OCR off: every page has a text layer, and OCR only adds time and noise.
- TableFormer ACCURATE with cell matching: table cells take their text from the PDF's
  own text cells, which matters for the two-column module tables.
The output is the full DoclingDocument (with page provenance for every item), never
the Markdown export: segmentation and citations need page numbers.
"""

import importlib.metadata
import time
from pathlib import Path

from pydantic import BaseModel


class ExtractStats(BaseModel):
    pdf_name: str
    page_range: tuple[int, int] | None
    pages_converted: int
    tables: int
    texts: int
    seconds: float
    docling_version: str
    options: dict[str, str | int | bool]


def build_converter(num_threads: int = 8, cell_matching: bool = True):
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        TableFormerMode,
        TableStructureOptions,
    )
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions()
    opts.do_ocr = False  # F1: digital PDF (Docling's default is True)
    opts.do_table_structure = True
    table_opts = TableStructureOptions(mode=TableFormerMode.ACCURATE, do_cell_matching=cell_matching)
    opts.table_structure_options = table_opts
    opts.accelerator_options.num_threads = num_threads
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    options: dict[str, str | int | bool] = {
        "do_ocr": opts.do_ocr,
        "do_table_structure": opts.do_table_structure,
        "table_mode": table_opts.mode.value,
        "do_cell_matching": table_opts.do_cell_matching,
        "num_threads": num_threads,
    }
    return converter, options


def extract(
    pdf_path: Path,
    out_json: Path,
    page_range: tuple[int, int] | None = None,
    num_threads: int = 8,
    cell_matching: bool = True,
) -> ExtractStats:
    """Convert the PDF (or a 1-based inclusive page range) and save the DoclingDocument JSON.

    Writes `out_json` and a sibling `<name>.stats.json` with runtime and options.
    """
    converter, options = build_converter(num_threads, cell_matching)
    started = time.perf_counter()
    if page_range:
        result = converter.convert(str(pdf_path), page_range=page_range)
    else:
        result = converter.convert(str(pdf_path))
    seconds = time.perf_counter() - started
    doc = result.document

    out_json.parent.mkdir(parents=True, exist_ok=True)
    doc.save_as_json(out_json)
    stats = ExtractStats(
        pdf_name=pdf_path.name,
        page_range=page_range,
        pages_converted=len(doc.pages),
        tables=len(doc.tables),
        texts=len(doc.texts),
        seconds=round(seconds, 1),
        docling_version=importlib.metadata.version("docling"),
        options=options,
    )
    stats_path(out_json).write_text(stats.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return stats


def stats_path(out_json: Path) -> Path:
    return out_json.with_name(out_json.stem + ".stats.json")
