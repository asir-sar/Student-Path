import pytest

from student_path.ingestion.probe import parse_stand_date, probe
from student_path.settings import get_settings

# The catalogue version this pipeline is built and validated against (README, "Data source").
EXPECTED_SHA256 = "1ddab2760962bfece10400035f8da10c426d65e12d02ebf830e4f4b965c291fc"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Stand: 13. Oktober 2025", "2025-10-13"),
        ("... Stand:  1. März 2024\r\n", "2024-03-01"),
        ("Stand: 5. Mai 2026", "2026-05-05"),
        ("Last revised: October 13, 2025", None),
        ("Stand: 13. Brumaire 2025", None),
    ],
)
def test_parse_stand_date(text, expected):
    assert parse_stand_date(text) == expected


@pytest.fixture(scope="module")
def manifest():
    return probe(get_settings().pdf_path)


def test_source_is_the_expected_catalogue(manifest):
    """Source contract: if this fails, a different PDF is in data/source/ and Phase 1 must be re-validated."""
    assert manifest.pdf_sha256 == EXPECTED_SHA256
    assert manifest.catalogue_version == "2025-10-13"


def test_every_page_has_a_text_layer(manifest):
    assert manifest.pages == 603
    assert manifest.pages_without_text == []


def test_outline_has_one_bookmark_per_module(manifest):
    assert manifest.bookmarks == 204  # 201 modules + Baukasten + 2 sample study plans
    assert manifest.module_bookmarks == 201
