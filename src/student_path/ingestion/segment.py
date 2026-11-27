"""P1.3: segment the catalogue into modules using the PDF's own bookmarks (ADR-005).

Each module becomes a page range keyed by its exam number (PN). Later steps read only a
module's own pages, so text can never bleed from one module into another (the main
defect of the v1 normalizer). Gate: tests/test_segment.py. Output of
`uv run sp ingest segment`: data/interim/segments.jsonl.

Facts this relies on (from P1.1 and the data audit):
- 204 bookmarks; the 201 whose title contains "PN <6 chars>" are the modules (PN_RE below).
- A module starts on its bookmarked page and ends on the page before the next module
  starts. The last module ends on the last page of the PDF (603).
- Titles look like " 5622 Software-SicherheitPN 405143  System Security",
  "SeminarPN 450001", " 32866 Entrepreneurship Development ProgrammePN 568320".
  The leading 4- or 5-digit number is the module_id; some modules have none.
- One module has the placeholder PN "xxxxxx": key it as "new-<module_id>" (ADR-006).
- pypdfium2 v5: `pdf.get_toc()` yields bookmarks with `.get_title()` and
  `.get_dest().get_index()` (0-based page index; `get_dest()` can return None).
  Close the document when done (`pdf.close()`), e.g. in a try/finally.
"""

import re
from pathlib import Path

import pypdfium2 as pdfium
from pydantic import BaseModel

PN_RE = re.compile(r"PN\s*([0-9x]{6})")
MODULE_ID_RE = re.compile(r"^\s*(\d{4,5})\b")

# Fixed page ranges (1-based, inclusive) of the front matter, checked against the PDF text.
FRONT_MATTER: dict[str, tuple[int, int]] = {
    "abbreviations": (2, 2),
    "regulations": (3, 4),  # German p. 3, English p. 4
    "module_overview": (5, 16),  # module-group tables: PN, SWS, ECTS, professor, language
    "degree_rules": (17, 18),  # "Hinweise" (120/40/30 ECTS), Baukasten, AStuPO § 9 (3) note
    "sample_plans": (19, 21),
    "table_of_contents": (22, 31),
}


class Segment(BaseModel):
    pn: str  # primary key (exam number); "new-<module_id>" for the placeholder "xxxxxx"
    module_id: str | None  # 4/5-digit catalogue number, NOT unique (5851, 5853); None if absent
    title_raw: str  # bookmark title, stripped
    page_start: int  # 1-based, inclusive (same numbering as Docling's page_no)
    page_end: int  # 1-based, inclusive

    @property
    def pages(self) -> int:
        return self.page_end - self.page_start + 1


def segment_modules(pdf_path: Path) -> list[Segment]:
    """Return one Segment per module, in document order.

    A module runs from its bookmarked page to the page before the next module's
    bookmark; the last module runs to the end of the PDF.
    """
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        last_page = len(pdf)
        starts: list[tuple[str, int]] = []  # (bookmark title, 1-based start page) of each module
        for bookmark in pdf.get_toc():
            dest = bookmark.get_dest()
            title = bookmark.get_title() or ""
            if dest is None or not PN_RE.search(title):
                continue  # not a module (Baukasten, sample study plans) or no target page
            index = dest.get_index()
            if index is None:
                continue
            starts.append((title, index + 1))  # pdfium is 0-based, our pages are 1-based
    finally:
        pdf.close()

    segments: list[Segment] = []
    for i, (title, page_start) in enumerate(starts):
        page_end = starts[i + 1][1] - 1 if i + 1 < len(starts) else last_page
        pn_match = PN_RE.search(title)
        assert pn_match is not None  # filtered above
        id_match = MODULE_ID_RE.match(title)
        module_id = id_match.group(1) if id_match else None
        pn = pn_match.group(1)
        if pn == "xxxxxx":  # module without an exam number yet (ADR-006)
            pn = f"new-{module_id}"
        segments.append(
            Segment(
                pn=pn, module_id=module_id, title_raw=title.strip(), page_start=page_start, page_end=page_end
            )
        )
    return segments


def write_segments(segments: list[Segment], out_path: Path) -> None:
    """One JSON object per line (JSONL), so later steps can stream and diff it."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for seg in segments:
            f.write(seg.model_dump_json() + "\n")
