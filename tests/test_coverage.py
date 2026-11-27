from pathlib import Path

import pytest

from student_path.ingestion.coverage import coverage, text_coverage
from student_path.settings import get_settings

SOFT_BREAK = "\ufffe"  # how pdfium marks a line-break hyphen in the text layer
NL = "\r\n"


@pytest.mark.parametrize(
    "pdf_text, docling_text",
    [
        # real cases from the catalogue
        (f"Informationsabruftechni{SOFT_BREAK}ken", "Informationsabruftechniken"),  # p. 33, Docling joined
        (f"der Stu{SOFT_BREAK}dierenden", "der Stu- dierenden"),  # p. 272, Docling kept the split
        # p. 49: the text layer interleaves the label column between the two halves of a word
        (
            f"forensischen Analy{SOFT_BREAK}{NL}Course content{NL}sis",
            "forensischen Analysis | Course content",
        ),
        (f"Overview of Acade{SOFT_BREAK}{NL}mic principles", "Overview of Acade | mic principles"),
        (f"KI-{NL}gestützten IT-Security", "KI-gestützten IT- Security"),  # real hyphen at a line end
        ("Informations- und Kommunikationssysteme", "Informations- und Kommunikationssysteme"),
    ],
)
def test_layout_differences_are_not_counted_as_loss(pdf_text, docling_text):
    _, share, missing = coverage(pdf_text, docling_text)
    assert share == 1.0, missing


def test_a_dropped_cell_is_detected_even_with_common_words():
    pdf_text = "The students present the results. The students write a report about the project."
    docling_text = "The students present the results."  # second sentence lost
    total, share, missing = coverage(pdf_text, docling_text)
    assert total == 12  # words of 2+ characters; "a" is not counted
    assert share == pytest.approx(5 / 12)
    assert {"write", "report", "project"} <= set(missing)


def test_full_extraction_meets_the_p12_gate():
    """P1.2 gate: Docling keeps >= 99.5% of the text layer overall and no page is largely lost.

    Known weak pages (long table cells dropped by Docling's cell matching, about 25 pages
    below 99%) are listed by `sp ingest coverage` and tracked in the QA report (P1.12).
    """
    full = Path(get_settings().interim_dir / "docling.json")
    if not full.exists():
        pytest.skip("run `uv run sp ingest extract` first")
    pages = text_coverage(get_settings().pdf_path, full)
    assert len(pages) == 603
    words = sum(p.pdf_words for p in pages)
    overall = sum(p.pdf_words * p.covered for p in pages) / words
    assert overall >= 0.995, overall
    worst = min(pages, key=lambda p: p.covered)
    assert worst.covered >= 0.80, (worst.page, worst.covered, worst.missing_sample)


def test_trial_extraction_covers_its_pages():
    trial = Path(get_settings().interim_dir / "docling_p49-51.json")
    if not trial.exists():
        pytest.skip("run `uv run sp ingest extract --pages 49-51` first")
    for page in text_coverage(get_settings().pdf_path, trial):
        assert page.covered >= 0.99, (page.page, page.missing_sample)
