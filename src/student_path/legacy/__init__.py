"""Legacy v1 ingestion code. Superseded; do not build on it.

Kept only as the "old" baseline for experiment E1 in context/IMPLEMENTATION_PLAN.md:
- parser.py: Docling run with OCR on, Markdown + JSON export
- normalizer.py: regex over the Markdown tables. Measured on the 201 real modules,
  it fills about 47% of fields and merges or duplicates modules (findings F5/F6).
- regex_parser.py: the earlier pipe-table parser (former test.py, see ADR-001)

The v2 pipeline (bookmark segmentation, label anchors, validation) is built in
phase P1 under student_path.ingestion. Outputs of this code live in data/legacy/.
"""
