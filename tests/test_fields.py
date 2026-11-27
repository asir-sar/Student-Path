"""P1.4 gate: every module gets all 17 fields, values stay in their own field across page
breaks, and assembly loses no text."""

import pypdfium2 as pdfium
import pytest

from student_path.ingestion.coverage import coverage
from student_path.ingestion.fields import FIELD_KEYS, SOFT_HYPHEN, ModuleFields, assemble_all, label_key
from student_path.ingestion.segment import segment_modules
from student_path.settings import get_settings

RUNNING_HEADER = "Modulkatalog Module Descriptions"


@pytest.fixture(scope="module")
def segments():
    return segment_modules(get_settings().pdf_path)


@pytest.fixture(scope="module")
def modules(segments) -> list[ModuleFields]:
    return assemble_all(get_settings().pdf_path, segments)


@pytest.fixture(scope="module")
def by_pn(modules) -> dict[str, ModuleFields]:
    return {m.pn: m for m in modules}


@pytest.mark.parametrize(
    "line, key",
    [
        ("Häufigkeit des Modulangebots", "frequency"),
        ("Frequency of course offering", "frequency"),
        ("Voraussetzungen nach Prü\u00ad", "prereq_formal"),
        ("Required prerequisites as per", "prereq_formal"),
        ("Studien-/Prüfungsleistungen", "assessment"),
        ("ECTS Credits", "ects"),
        ("Inhalt", "content"),
        ("Literatur", "literature"),
        # continuation lines of a label, and the module number: not a new field
        ("fungsordnung", None),
        ("the study and examination", None),
        ("regulations", None),
        ("5622", None),
    ],
)
def test_label_key(line, key):
    assert label_key(line) == key


def test_one_record_per_module_in_document_order(modules, segments):
    assert [m.pn for m in modules] == [s.pn for s in segments]


def test_every_module_has_every_label_once(modules):
    assert all(m.missing == [] for m in modules), [(m.pn, m.missing) for m in modules if m.missing]
    assert all(m.repeated == [] for m in modules), [(m.pn, m.repeated) for m in modules if m.repeated]


def test_empty_values_only_where_the_catalogue_has_none(modules):
    # PN 568320 (Entrepreneurship Development Programme) prints both rows without a value
    assert [(m.pn, m.empty) for m in modules if m.empty] == [("568320", ["prereq_recommended", "media"])]


def test_header_carries_the_exam_number(modules):
    for m in modules:
        marker = "xxxxxx" if m.pn.startswith("new-") else m.pn
        assert marker in m.header, (m.pn, m.header)
        if m.module_id:
            assert m.module_id in m.header, (m.pn, m.header)


def test_system_security_fields(by_pn):
    m = by_pn["405143"]
    f = m.fields
    assert m.header.splitlines() == ["5622", "Software-Sicherheit PN 405143", "System Security"]
    assert f["ects"] == "5"
    assert f["lecturer"] == "Posegga"
    assert f["frequency"] == "Jedes Sommersemester\nEvery summer semester"
    assert f["prereq_recommended"] == "Advanced IT Security"
    assert "Writing Secure Code" in f["literature"]


def test_values_continued_on_the_next_page_stay_in_their_field(by_pn):
    """Finding F8: Docling put the tail of the learning outcomes ("mic principles ...") into
    the content field. By geometry, it stays with the outcomes."""
    f = by_pn["405143"]
    assert f.fields["learning_outcomes"].endswith("mic principles to practical requirements.")
    assert f.fields["content"].startswith("Der Inhalt des Moduls")
    assert "selbsterarbeitetes Thema" in f.fields["assessment"]  # continues on the next page
    assert f.field_pages["assessment"] == [49, 50]


def test_line_break_hyphens_are_soft_hyphens(modules):
    text = "".join(v for m in modules for v in m.fields.values())
    assert "\x02" not in text and "\ufffe" not in text
    assert text.count(SOFT_HYPHEN) > 3000  # 3,676 line-break hyphens on the module pages


def test_assembly_loses_no_text(modules):
    """Every word on a module's pages, except the running header and the page number,
    reappears in its header, labels or field values."""
    pdf = pdfium.PdfDocument(str(get_settings().pdf_path))
    try:
        for m in modules:
            truth = []
            for page_no in range(m.page_start, m.page_end + 1):
                page = pdf[page_no - 1]
                textpage = page.get_textpage()
                text = textpage.get_text_range().replace(RUNNING_HEADER, "")
                textpage.close()
                page.close()
                truth.append(text.rstrip().removesuffix(str(page_no)))
            assembled = "\n".join([m.header, *m.labels_raw.values(), *m.fields.values()])
            _, share, missing = coverage("\n".join(truth), assembled.replace(SOFT_HYPHEN, "\ufffe"))
            assert share >= 0.999, (m.pn, share, missing)
    finally:
        pdf.close()


def test_field_keys_are_the_17_catalogue_fields():
    assert len(FIELD_KEYS) == 17
