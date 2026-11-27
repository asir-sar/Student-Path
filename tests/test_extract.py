import json

import pytest

from student_path.ingestion.extract import extract, stats_path
from student_path.settings import get_settings

pytestmark = pytest.mark.slow  # runs real Docling inference (~30 s); run with: uv run pytest -m slow


def test_extract_one_page_keeps_provenance_and_ocr_off(tmp_path):
    out = tmp_path / "docling.json"
    stats = extract(get_settings().pdf_path, out, page_range=(48, 48), num_threads=4)

    assert stats.pages_converted == 1
    assert stats.options["do_ocr"] is False
    assert stats.options["table_mode"] == "accurate"
    assert stats.tables >= 1  # page 48 starts System Security (PN 405143) with its module table

    doc = json.loads(out.read_text(encoding="utf-8"))
    pages = {p["page_no"] for item in doc["texts"] + doc["tables"] for p in item.get("prov", [])}
    assert pages == {48}
    assert json.loads(stats_path(out).read_text(encoding="utf-8"))["pages_converted"] == 1

    table_text = " ".join(cell["text"] for cell in doc["tables"][0]["data"]["table_cells"])
    assert "Posegga" in table_text
