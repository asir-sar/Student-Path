"""P1.1: probe the source PDF and describe it in a manifest.

The manifest pins down exactly which catalogue the pipeline was built from (checksum,
version date) and records the structural facts the rest of Phase 1 relies on:
every page has a text layer (so OCR stays off) and the outline has one bookmark
per module carrying its exam number (PN), which drives segmentation in P1.3.
"""

import hashlib
import re
from datetime import UTC, date, datetime
from pathlib import Path

import pypdfium2 as pdfium
from pydantic import BaseModel

PN_RE = re.compile(r"PN\s*([0-9x]{6})")
STAND_RE = re.compile(r"Stand:\s*(\d{1,2})\.\s*([A-Za-zÄäÖöÜü]+)\s+(\d{4})")
GERMAN_MONTHS = {
    "januar": 1, "jänner": 1, "februar": 2, "märz": 3, "april": 4, "mai": 5, "juni": 6,
    "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12,
}  # fmt: skip
MIN_TEXT_CHARS = 30  # a page with less text than this is treated as having no text layer


class Manifest(BaseModel):
    pdf_name: str
    pdf_sha256: str
    size_bytes: int
    pages: int
    pages_without_text: list[int]  # 1-based page numbers
    text_layer_chars: int
    catalogue_version: str | None  # ISO date parsed from "Stand: 13. Oktober 2025" on page 1
    bookmarks: int
    module_bookmarks: int  # bookmarks that carry an exam number (PN)
    probed_at: str


def parse_stand_date(text: str) -> str | None:
    """Return the ISO date of the first "Stand: <d>. <Monat> <yyyy>" in text, or None."""
    m = STAND_RE.search(text)
    if not m:
        return None
    month = GERMAN_MONTHS.get(m.group(2).lower())
    if month is None:
        return None
    return date(int(m.group(3)), month, int(m.group(1))).isoformat()


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(pdf_path: Path) -> Manifest:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        pages_without_text: list[int] = []
        total_chars = 0
        first_page_text = ""
        for i in range(len(pdf)):
            page = pdf[i]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            textpage.close()
            page.close()
            if i == 0:
                first_page_text = text
            total_chars += len(text)
            if len(text.strip()) < MIN_TEXT_CHARS:
                pages_without_text.append(i + 1)
        titles = [bm.get_title() or "" for bm in pdf.get_toc()]
        return Manifest(
            pdf_name=pdf_path.name,
            pdf_sha256=sha256_of(pdf_path),
            size_bytes=pdf_path.stat().st_size,
            pages=len(pdf),
            pages_without_text=pages_without_text,
            text_layer_chars=total_chars,
            catalogue_version=parse_stand_date(first_page_text),
            bookmarks=len(titles),
            module_bookmarks=sum(1 for t in titles if PN_RE.search(t)),
            probed_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
    finally:
        pdf.close()


def write_manifest(manifest: Manifest, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
