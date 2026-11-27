"""P1.4: assemble each module's raw fields from the PDF text layer, by page geometry (ADR-015).

Every module page has the same two-column table: field labels on the left (text starts at
x = 77-81 pt), values on the right (x >= 223 pt); nothing starts in between. A field begins
where a label line matches one of the 17 known labels, and its value is all right-column
text from there to the next label, across page breaks. Working on the text layer instead of
Docling's table grid has three effects, measured in P1.2/P1.4:
- no text is lost (Docling's cell matching drops cells in long tables, finding F13);
- a value continued on the next page stays with its own field, so the page-break "bleed"
  of finding F8 cannot happen;
- line-break hyphens are known exactly (pdfium marks them) and kept as soft hyphens
  (U+00AD) for de-hyphenation in P1.5.
Values are raw: lines joined with newlines, German and English interleaved, soft hyphens
kept. Cleaning and typing are later steps.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pypdfium2 as pdfium
from pydantic import BaseModel

from student_path.ingestion.segment import Segment

LABEL_COLUMN_MAX_X = 220.0  # label text starts at x=77-81, value text at x>=223 (all module pages)
HEADER_MIN_Y = 800.0  # running page header "Modulkatalog Module Descriptions" (y = 810-820)
FOOTER_MAX_Y = 65.0  # page number (y = 53-61)
SAME_LINE_OVERLAP = 0.4  # runs overlapping vertically by this share of the smaller height are one line
# pt: runs closer than this are one word. Measured on all module pages: gaps inside a word
# (superscripts "L"+"1", symbols "σ"+"-Algebra", punctuation) are <= 1.7 pt; word gaps are >= 3.6 pt
TOUCHING_GAP = 2.5
LABEL_TOLERANCE = 3.0  # pt: a value line may start this much above its label line
SOFT_HYPHEN = "\u00ad"  # marks a hyphen that only exists because the line wrapped

# Start of a label line, German or English, as printed in the label column (checked on all modules).
LABELS: dict[str, str] = {
    "frequency": r"Häufigkeit des Modulangebots|Frequency of course offering",
    "duration": r"Moduldauer|Module duration",
    "convenor": r"Modulverantwortliche|Module convenor",
    "lecturer": r"Dozent|Lecturer",
    "language": r"Sprache|Language of instruction",
    "curriculum": r"Zuordnung zum Curriculum|Curriculum\b",
    "contact_hours": r"Lehrform|Contact hours",
    "workload": r"Arbeitsaufwand|Workload",
    "ects": r"ECTS|Credits\b",
    "prereq_formal": r"Voraussetzungen nach|Required prerequisites",
    "prereq_recommended": r"Empfohlene Vorkenntnisse|Recommended skills",
    "applicability": r"Verwendbarkeit|Applicability",
    "learning_outcomes": r"Angestrebte Lernergebnisse|Learning outcomes",
    "content": r"Inhalt\b|Course content",
    "assessment": r"Studien-?\s*/\s*Prüfungsleistungen|Assessment",
    "media": r"Medienformen|Media used",
    "literature": r"Literatur\b|Reading list",
}
FIELD_KEYS: tuple[str, ...] = tuple(LABELS)
_LABEL_RE = {key: re.compile(rf"^(?:{pattern})") for key, pattern in LABELS.items()}


def label_key(line: str) -> str | None:
    """The field a label-column line starts, or None (label continuation, module number, ...)."""
    return next((key for key, rx in _LABEL_RE.items() if rx.match(line)), None)


@dataclass(frozen=True)
class Run:
    """One text run from pdfium: a piece of a line in a single font."""

    bottom: float
    top: float
    left: float
    right: float
    text: str


@dataclass(frozen=True)
class Line:
    page: int
    top: float  # PDF coordinates: larger is higher on the page
    column: Literal["label", "value"]
    text: str


class ModuleFields(BaseModel):
    pn: str
    module_id: str | None
    page_start: int
    page_end: int
    header: str  # text above the first label: module number, titles, exam number
    fields: dict[str, str]  # field key -> raw value text (lines joined with "\n", soft hyphens kept)
    field_pages: dict[str, list[int]]  # field key -> pages the value text is on (for citations)
    labels_raw: dict[str, str]  # field key -> the label text as printed (for QA)
    missing: list[str]  # field keys whose label was not found
    empty: list[str]  # field keys whose label is there but whose value cell is empty
    repeated: list[str]  # field keys whose label occurs again after another field started


def page_lines(textpage: pdfium.PdfTextPage, page_no: int) -> list[Line]:
    """Text runs of one page grouped into lines per column, top to bottom, without header/footer."""
    runs: list[Run] = []
    for i in range(textpage.count_rects()):
        left, bottom, right, top = textpage.get_rect(i)
        centre = (top + bottom) / 2
        if centre >= HEADER_MIN_Y or centre <= FOOTER_MAX_Y:
            continue
        # pdfium returns a line-break hyphen as U+0002 here (U+FFFE in get_text_range); keep it
        # as the standard soft hyphen so P1.5 can tell it from a real hyphen
        text = textpage.get_text_bounded(left, bottom, right, top).replace("\x02", SOFT_HYPHEN).strip()
        if text:
            runs.append(Run(bottom=bottom, top=top, left=left, right=right, text=text))
    lines: list[Line] = []
    for column in ("label", "value"):
        in_column = sorted(
            (r for r in runs if (r.left < LABEL_COLUMN_MAX_X) == (column == "label")),
            key=lambda r: (-(r.top + r.bottom), r.left),
        )
        group: list[Run] = []
        for run in in_column:
            if group and not _same_line(group, run):
                lines.append(_line(page_no, column, group))
                group = []
            group.append(run)
        if group:
            lines.append(_line(page_no, column, group))
    return lines


def _same_line(group: list["Run"], run: "Run") -> bool:
    """True if run overlaps the group vertically by at least SAME_LINE_OVERLAP of the smaller height.

    This keeps a raised superscript ("L" + "1" in L^1) on its base line, while two
    neighbouring text lines (15 pt apart, 10 pt high) never overlap.
    """
    low, high = min(r.bottom for r in group), max(r.top for r in group)
    overlap = min(high, run.top) - max(low, run.bottom)
    smaller = min(high - low, run.top - run.bottom)
    return smaller > 0 and overlap >= SAME_LINE_OVERLAP * smaller


def _line(page_no: int, column: Literal["label", "value"], group: list["Run"]) -> Line:
    runs = sorted(group, key=lambda r: r.left)
    text = runs[0].text
    for prev, run in zip(runs, runs[1:], strict=False):
        text += ("" if run.left - prev.right < TOUCHING_GAP else " ") + run.text
    return Line(page=page_no, top=max(r.top for r in runs), column=column, text=text)


def assemble(segment: Segment, lines: list[Line]) -> ModuleFields:
    """Assign the lines of one module to its header and fields."""

    # Reading order; a label line sorts slightly earlier so that value text starting a hair
    # above its label (same table row) is not given to the previous field.
    def order(line: Line) -> tuple[int, float, int]:
        lift = LABEL_TOLERANCE if line.column == "label" else 0.0
        return (line.page, -(line.top + lift), 0 if line.column == "label" else 1)

    header: list[str] = []
    values: dict[str, list[str]] = {}
    pages: dict[str, list[int]] = {}
    labels: dict[str, list[str]] = {}
    repeated: list[str] = []
    current: str | None = None
    for line in sorted(lines, key=order):
        if line.column == "label":
            key = label_key(line.text)
            if key is not None and key != current:
                if key in values:
                    repeated.append(key)
                current = key
                values.setdefault(key, [])
                pages.setdefault(key, [])
            if current is not None:
                labels.setdefault(current, []).append(line.text)  # label (or its continuation line)
            else:
                header.append(line.text)  # module number, often with the start of the title
            continue
        if current is None:
            header.append(line.text)
            continue
        values[current].append(line.text)
        if line.page not in pages[current]:
            pages[current].append(line.page)
    return ModuleFields(
        pn=segment.pn,
        module_id=segment.module_id,
        page_start=segment.page_start,
        page_end=segment.page_end,
        header="\n".join(header),
        fields={key: "\n".join(text) for key, text in values.items()},
        field_pages=pages,
        labels_raw={key: " ".join(text) for key, text in labels.items()},
        missing=[key for key in FIELD_KEYS if key not in values],
        empty=[key for key in FIELD_KEYS if key in values and not values[key]],
        repeated=sorted(set(repeated)),
    )


def assemble_all(pdf_path: Path, segments: list[Segment]) -> list[ModuleFields]:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        result = []
        for segment in segments:
            lines: list[Line] = []
            for page_no in range(segment.page_start, segment.page_end + 1):
                page = pdf[page_no - 1]
                textpage = page.get_textpage()
                lines.extend(page_lines(textpage, page_no))
                textpage.close()
                page.close()
            result.append(assemble(segment, lines))
        return result
    finally:
        pdf.close()


def read_segments(path: Path) -> list[Segment]:
    with path.open(encoding="utf-8") as f:
        return [Segment.model_validate(json.loads(line)) for line in f if line.strip()]


def write_fields(modules: list[ModuleFields], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for module in modules:
            f.write(module.model_dump_json() + "\n")
