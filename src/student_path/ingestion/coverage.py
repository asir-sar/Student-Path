"""P1.2 quality check: does the Docling output still contain all the text of the PDF?

Compares, page by page, the words of the PDF's own text layer (the ground truth for a
digital PDF) with the text Docling produced for that page (text items + table cells).
Coverage is the share of text-layer words, counted with multiplicity, found again in
Docling's output. A drop below ~99% means text was lost, e.g. table cells that Docling
could not place in its predicted grid.

Two ordering effects make naive word matching unfair, and both are handled:
- The text layer runs line by line across both table columns, so a word hyphenated at a
  line end ("Analy" + U+FFFE) is continued only after the other column's line ("sis").
- Docling sometimes joins hyphenated words ("Informationsabruftechniken"), sometimes keeps
  the split ("Stu- dierenden"), and a page break can split a word across two cells.
So both sides are split into the same pieces (at hyphens and line-break markers), matched
exactly first; a leftover piece then counts as covered only if Docling has no exact
occurrence of it but contains it inside its de-hyphenated text (a fragment of a joined
word). Real loss stays visible: a dropped cell's common words ("the", "students") have
exact occurrences elsewhere, so their missing copies are not excused.
"""

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pypdfium2 as pdfium
from pydantic import BaseModel

SOFT_BREAK = "￾"  # pdfium's marker for a line-break hyphen
WORD_RE = re.compile(r"\w{2,}")
JOIN_HYPHEN_RE = re.compile(r"(?<=\w)-\s*(?=\w)")


class PageCoverage(BaseModel):
    page: int
    pdf_words: int
    covered: float  # 0..1
    missing_sample: list[str]  # up to 8 text-layer words that Docling lost


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


def words(text: str) -> Counter[str]:
    """Word pieces: hyphens and line-break markers split words, identically on both sides."""
    return Counter(WORD_RE.findall(_normalize(text.replace(SOFT_BREAK, " "))))


def joined_text(text: str) -> str:
    """Docling text with hyphenated words joined, for the fragment fallback."""
    return JOIN_HYPHEN_RE.sub("", _normalize(text.replace(SOFT_BREAK, "")))


def coverage(pdf_text: str, docling_text: str) -> tuple[int, float, list[str]]:
    """Return (text-layer word count, covered share, sample of missing words) for one page."""
    truth, got = words(pdf_text), words(docling_text)
    blob = joined_text(docling_text)
    total = sum(truth.values())
    covered = 0
    missing: Counter[str] = Counter()
    for word, n in truth.items():
        exact = min(n, got[word])
        covered += exact
        leftover = n - exact
        if leftover and got[word] == 0 and word in blob:
            covered += leftover  # fragment of a word that Docling joined or split differently
        elif leftover:
            missing[word] = leftover
    return total, (covered / total if total else 1.0), [w for w, _ in missing.most_common(8)]


def docling_text_by_page(doc_json: Path) -> dict[int, str]:
    doc = json.loads(doc_json.read_text(encoding="utf-8"))
    parts: dict[int, list[str]] = defaultdict(list)
    for item in doc.get("texts", []):
        for prov in item.get("prov", []):
            parts[prov["page_no"]].append(item.get("text", ""))
    for table in doc.get("tables", []):
        provs = table.get("prov", [])
        if provs:  # a table item never spans pages
            parts[provs[0]["page_no"]].extend(c.get("text", "") for c in table["data"]["table_cells"])
    # every converted page gets an entry, even if Docling produced no text for it at all
    texts = {int(page): "" for page in doc.get("pages", {})}
    texts.update({page: "\n".join(chunks) for page, chunks in parts.items()})
    return texts


def text_coverage(pdf_path: Path, doc_json: Path, pages: list[int] | None = None) -> list[PageCoverage]:
    """Coverage per page (1-based). Defaults to every page that Docling converted, so a page
    whose text was lost entirely still counts (with coverage 0)."""
    docling = docling_text_by_page(doc_json)
    pages = sorted(docling) if pages is None else pages
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        result = []
        for page_no in pages:
            page = pdf[page_no - 1]
            textpage = page.get_textpage()
            truth = textpage.get_text_range()
            textpage.close()
            page.close()
            total, share, missing = coverage(truth, docling.get(page_no, ""))
            result.append(PageCoverage(page=page_no, pdf_words=total, covered=share, missing_sample=missing))
        return result
    finally:
        pdf.close()
