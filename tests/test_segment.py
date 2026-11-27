"""P1.3 gate: these tests define "done" for segment_modules (owner-implemented)."""

import pypdfium2 as pdfium
import pytest

from student_path.ingestion.segment import FRONT_MATTER, Segment, segment_modules
from student_path.settings import get_settings


@pytest.fixture(scope="module")
def segments() -> list[Segment]:
    return segment_modules(get_settings().pdf_path)


@pytest.fixture(scope="module")
def by_pn(segments) -> dict[str, Segment]:
    return {s.pn: s for s in segments}


def test_exactly_201_modules_with_unique_keys(segments):
    assert len(segments) == 201
    assert len({s.pn for s in segments}) == 201


def test_pages_are_contiguous_and_cover_every_module_page(segments):
    assert segments[0].page_start == 32
    assert segments[-1].page_end == 603
    for prev, cur in zip(segments, segments[1:], strict=False):
        assert cur.page_start == prev.page_end + 1, (prev.pn, cur.pn)
    assert all(2 <= s.pages <= 6 for s in segments)


def test_first_last_and_a_known_module(by_pn, segments):
    assert (segments[0].pn, segments[0].module_id, segments[0].page_start, segments[0].page_end) == (
        "455320", "5487", 32, 35,
    )  # fmt: skip
    thesis = segments[-1]
    assert (thesis.pn, thesis.module_id, thesis.page_start) == ("459900", None, 601)
    sec = by_pn["405143"]  # System Security
    assert (sec.module_id, sec.page_start, sec.page_end) == ("5622", 48, 50)


def test_module_id_is_not_unique(segments):
    def pns(module_id: str) -> set[str]:
        return {s.pn for s in segments if s.module_id == module_id}

    assert pns("5851") == {"455369", "455407"}
    assert pns("5853") == {"455375", "455435"}


def test_modules_without_a_four_digit_id(segments):
    no_id = [s for s in segments if s.module_id is None]
    five_digit = sorted(s.module_id for s in segments if s.module_id and len(s.module_id) == 5)
    assert len(no_id) == 9
    assert {"450001", "407680", "458999", "459900"} <= {s.pn for s in no_id}
    assert five_digit == ["32866", "39734", "39745", "39746"]


def test_placeholder_exam_number_gets_a_synthetic_key(by_pn):
    assert "xxxxxx" not in by_pn
    new = by_pn["new-6133"]
    assert (new.module_id, new.page_start, new.page_end) == ("6133", 503, 504)


def test_each_module_starts_on_its_own_page(segments):
    """Independent check against the page text: the module's PN (or ID) is printed on its start page."""
    pdf = pdfium.PdfDocument(str(get_settings().pdf_path))
    try:
        for s in segments:
            page = pdf[s.page_start - 1]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            textpage.close()
            page.close()
            marker = s.module_id if s.pn.startswith("new-") else s.pn
            assert marker in text, (s.pn, s.page_start)
    finally:
        pdf.close()


def test_front_matter_ends_before_the_first_module(segments):
    ranges = sorted(FRONT_MATTER.values())
    for (_, end), (start, _) in zip(ranges, ranges[1:], strict=False):
        assert end < start
    assert ranges[-1][1] < segments[0].page_start
