"""
LEGACY v1 normalizer (superseded, see student_path/legacy/__init__.py).

Normalize Docling output into structured module JSON.

Reads the raw Markdown output from Docling (or the structured JSON) and extracts
individual modules with their structured fields. Known limitations are listed in
context/IMPLEMENTATION_PLAN.md (findings F5/F6); phase P1 replaces this module.

Usage (see `uv run sp legacy normalize --help`):
    uv run sp legacy normalize
    uv run sp legacy normalize --input data/legacy/modulkatalog_docling.json --format json
    uv run sp legacy normalize --inspect   # print 5 random modules for a quality check
"""

import json
import os
import re
import random
from typing import Any


# ─── Field Mapping ────────────────────────────────────────────────────────────
# Maps known German/English field names from the PDF tables to our schema keys.
# The PDF uses bilingual labels; we normalize to a consistent English schema.

FIELD_MAP = {
    # Module identification
    "häufigkeit des modulangebots": "frequency",
    "frequency of course offering": "frequency",
    "moduldauer": "duration",
    "module duration": "duration",
    "modulverantwortliche": "convenor",
    "module convenor": "convenor",
    "dozent": "lecturer",
    "lecturer": "lecturer",
    "sprache": "language",
    "language of instruction": "language",

    # Curriculum placement
    "zuordnung zum curriculum": "curriculum",
    "curriculum": "curriculum",
    "modulgruppe": "focus_area",
    "focus": "focus_area",

    # Workload
    "lehrform": "contact_hours",
    "lehrform/sws": "contact_hours",
    "contact hours": "contact_hours",
    "arbeitsaufwand": "workload",
    "workload": "workload",
    "ects": "ects",
    "credits": "ects",

    # Prerequisites
    "voraussetzungen nach prüfungsordnung": "prerequisites_formal",
    "voraussetzungen nach prü": "prerequisites_formal",
    "required prerequisites": "prerequisites_formal",
    "empfohlene vorkenntnisse": "prerequisites_recommended",
    "recommended skills": "prerequisites_recommended",
    "recommended prerequisites": "prerequisites_recommended",

    # Content
    "verwendbarkeit": "applicability",
    "applicability": "applicability",
    "angestrebte lernergebnisse": "learning_outcomes",
    "learning outcomes": "learning_outcomes",
    "inhalt": "content",
    "course content": "content",

    # Assessment
    "studien-/prüfungsleistungen": "assessment",
    "studienleistungen": "assessment",
    "prüfungsleistungen": "assessment",
    "assessment": "assessment",

    # Media & Literature
    "medienformen": "media",
    "media used": "media",
    "literatur": "literature",
    "reading list": "literature",
}


def normalize_field_key(raw_key: str) -> str:
    """
    Match a raw field label from the PDF to our normalized schema key.
    Uses fuzzy matching since PDF extraction can introduce artifacts.
    """
    cleaned = raw_key.lower().strip()
    # Remove common artifacts
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'[()]', '', cleaned)

    # Try exact match first
    if cleaned in FIELD_MAP:
        return FIELD_MAP[cleaned]

    # Try partial match (field label might be truncated or have extra text)
    for pattern, key in FIELD_MAP.items():
        if pattern in cleaned or cleaned in pattern:
            return key

    # Unknown field — keep it with a prefix so we can identify gaps
    return f"_raw_{cleaned.replace(' ', '_')[:40]}"


def parse_semester(raw: str) -> str:
    """Extract semester offering from raw text."""
    lower = raw.lower()
    if "winter" in lower and "sommer" in lower or "winter" in lower and "summer" in lower:
        return "both"
    if "winter" in lower:
        return "winter"
    if "sommer" in lower or "summer" in lower:
        return "summer"
    return raw.strip()


def parse_ects(raw: str) -> int | None:
    """Extract ECTS credit points as integer."""
    match = re.search(r'(\d+)', raw)
    return int(match.group(1)) if match else None


def parse_language(raw: str) -> list[str]:
    """Extract language(s) of instruction."""
    lower = raw.lower()
    langs = []
    if "deutsch" in lower or "german" in lower:
        langs.append("de")
    if "englisch" in lower or "english" in lower:
        langs.append("en")
    return langs if langs else ["de"]  # Default to German


def append_text(current: str, new: str) -> str:
    """
    Append text, handling hyphenation across lines.
    Borrowed from test.py's useful logic.
    """
    if not new:
        return current
    if not current:
        return new
    stripped = current.rstrip()
    if stripped.endswith('-'):
        return stripped[:-1] + new
    return current + " " + new


# ─── Markdown Table Parser ────────────────────────────────────────────────────

def normalize_from_markdown(md_path: str) -> list[dict[str, Any]]:
    """
    Parse the Docling Markdown output and extract structured module records.

    The Modulkatalog PDF contains two-column tables where:
    - Column 1: Field labels (German + English)
    - Column 2: Field values
    - A new module starts when Column 1 contains a numeric module ID (3+ digits)
    """
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    modules = []
    current_module = None
    current_key = ""
    current_val = ""

    def flush_field():
        nonlocal current_key, current_val, current_module
        if current_module is not None and current_key:
            normalized_key = normalize_field_key(current_key)
            clean_val = re.sub(r'\s+', ' ', current_val).strip()
            if normalized_key in current_module and current_module[normalized_key]:
                current_module[normalized_key] += " " + clean_val
            else:
                current_module[normalized_key] = clean_val
        current_key = ""
        current_val = ""

    for line in lines:
        stripped = line.strip()

        # Skip empty, separator, and header/footer lines
        if not stripped:
            continue
        if re.match(r'^\|[\s\-:]+\|[\s\-:]+\|$', stripped):
            # Table separator row (|---|---|)
            continue
        if stripped in ("Modulkatalog", "Module Descriptions"):
            continue
        if re.match(r'^\d+$', stripped):
            continue

        # Only process table rows
        if not stripped.startswith("|"):
            continue

        # Split the pipe-delimited row
        parts = [p.strip() for p in stripped.split("|")]
        if len(parts) < 3:
            continue

        col1 = parts[1] if len(parts) > 1 else ""
        col2 = parts[2] if len(parts) > 2 else ""

        # Skip fully empty rows
        if not col1 and not col2:
            continue

        # Detect new module: Column 1 is a numeric ID (3+ digits)
        if re.match(r'^\d{3,}$', col1):
            flush_field()
            if current_module is not None:
                modules.append(current_module)

            current_module = {
                "module_id": col1,
                "module_name": col2,
            }
            continue

        # Inside a module — parse fields
        if current_module is not None:
            is_new_key = False
            if col1:
                if not current_key:
                    is_new_key = True
                elif current_key.rstrip().endswith('-'):
                    # Previous key was hyphenated — continuation
                    is_new_key = False
                elif col1[0].islower():
                    # Starts with lowercase — continuation of previous key
                    is_new_key = False
                else:
                    is_new_key = True

            if is_new_key:
                flush_field()
                current_key = col1
                current_val = col2
            else:
                current_key = append_text(current_key, col1)
                current_val = append_text(current_val, col2)

    # Flush last field and module
    flush_field()
    if current_module is not None:
        modules.append(current_module)

    return modules


# ─── Docling JSON Parser ──────────────────────────────────────────────────────

def normalize_from_docling_json(json_path: str) -> list[dict[str, Any]]:
    """
    Parse the Docling structured JSON output.
    This is an alternative path that uses Docling's own table structure
    detection instead of parsing the markdown.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    modules = []

    # Docling JSON structure: doc["tables"] contains detected tables
    tables = doc.get("tables", [])
    if not tables:
        # Fallback: check if tables are embedded in the document body
        print("  No 'tables' key in Docling JSON. Falling back to Markdown parser.")
        md_path = json_path.replace("_docling.json", "_raw.md")
        if os.path.exists(md_path):
            return normalize_from_markdown(md_path)
        return []

    for table in tables:
        # Each table in Docling has a grid structure
        grid = table.get("data", {}).get("grid", [])
        if not grid or len(grid) < 2:
            continue

        # Check if this looks like a module table (first cell is a numeric ID)
        first_cell = grid[0][0].get("text", "") if grid[0] else ""
        if re.match(r'^\d{3,}$', first_cell.strip()):
            module = {"module_id": first_cell.strip()}
            if len(grid[0]) > 1:
                module["module_name"] = grid[0][1].get("text", "").strip()

            for row in grid[1:]:
                if len(row) >= 2:
                    key = row[0].get("text", "").strip()
                    val = row[1].get("text", "").strip()
                    if key:
                        normalized_key = normalize_field_key(key)
                        module[normalized_key] = val

            modules.append(module)

    return modules


# ─── Post-Processing ──────────────────────────────────────────────────────────

def enrich_module(module: dict) -> dict:
    """
    Post-process a raw module dict into the final schema with typed fields.
    Adds structured metadata for Qdrant filtering.
    """
    enriched = {
        "module_id": module.get("module_id", ""),
        "module_name": module.get("module_name", ""),
    }

    # Split bilingual module name if possible
    name = module.get("module_name", "")
    # Common pattern: "German Name  English Name" or "German Name English Name PN XXXXXX"
    pn_match = re.search(r'\s+PN\s+\d+', name)
    if pn_match:
        enriched["pn_number"] = name[pn_match.start():].strip()
        name = name[:pn_match.start()].strip()

    enriched["module_name_raw"] = name

    # Parse structured fields
    enriched["ects"] = parse_ects(module.get("ects", ""))
    enriched["semester_offered"] = parse_semester(module.get("frequency", ""))
    enriched["language"] = parse_language(module.get("language", ""))
    enriched["duration"] = module.get("duration", "").strip()
    enriched["lecturer"] = module.get("lecturer", "").strip()
    enriched["convenor"] = module.get("convenor", "").strip()
    enriched["focus_area"] = module.get("focus_area", module.get("curriculum", "")).strip()

    # Prerequisites
    formal_prereq = module.get("prerequisites_formal", "")
    enriched["prerequisites_formal"] = formal_prereq.strip()
    enriched["has_prerequisites"] = bool(
        formal_prereq and formal_prereq.strip().lower() not in ("keine", "none", "no", "-", "")
    )
    enriched["prerequisites_recommended"] = module.get("prerequisites_recommended", "").strip()

    # Content fields (kept as-is for embedding)
    enriched["contact_hours"] = module.get("contact_hours", "").strip()
    enriched["workload"] = module.get("workload", "").strip()
    enriched["learning_outcomes"] = module.get("learning_outcomes", "").strip()
    enriched["content"] = module.get("content", "").strip()
    enriched["assessment"] = module.get("assessment", "").strip()
    enriched["media"] = module.get("media", "").strip()
    enriched["literature"] = module.get("literature", "").strip()
    enriched["applicability"] = module.get("applicability", "").strip()

    # Build the embedding text: a rich concatenation of all meaningful fields
    text_parts = [
        f"Module: {enriched['module_name_raw']}",
        f"ECTS: {enriched['ects']}" if enriched['ects'] else "",
        f"Semester: {enriched['semester_offered']}" if enriched['semester_offered'] else "",
        f"Language: {', '.join(enriched['language'])}",
        f"Focus: {enriched['focus_area']}" if enriched['focus_area'] else "",
        f"Lecturer: {enriched['lecturer']}" if enriched['lecturer'] else "",
        f"Prerequisites: {enriched['prerequisites_recommended']}" if enriched['prerequisites_recommended'] else "",
        f"Content: {enriched['content']}" if enriched['content'] else "",
        f"Learning Outcomes: {enriched['learning_outcomes']}" if enriched['learning_outcomes'] else "",
        f"Assessment: {enriched['assessment']}" if enriched['assessment'] else "",
    ]
    enriched["embedding_text"] = "\n".join(part for part in text_parts if part)

    # Preserve any raw/unmapped fields for debugging
    raw_fields = {k: v for k, v in module.items() if k.startswith("_raw_")}
    if raw_fields:
        enriched["_unmapped_fields"] = raw_fields

    return enriched


def normalize_modules(input_path: str, input_format: str = "auto") -> list[dict]:
    """
    Main normalization pipeline.
    Reads Docling output (markdown or JSON) and produces structured module records.
    """
    # Auto-detect format
    if input_format == "auto":
        if input_path.endswith(".json"):
            input_format = "json"
        else:
            input_format = "markdown"

    print(f"[1/3] Parsing {input_format} input: {input_path}")

    if input_format == "json":
        raw_modules = normalize_from_docling_json(input_path)
    else:
        raw_modules = normalize_from_markdown(input_path)

    print(f"[2/3] Found {len(raw_modules)} raw modules. Enriching...")

    enriched = [enrich_module(m) for m in raw_modules]

    # Filter out modules with no name (likely parsing artifacts)
    enriched = [m for m in enriched if m["module_name_raw"]]

    print(f"[3/3] Produced {len(enriched)} enriched modules")

    # Print stats
    with_ects = sum(1 for m in enriched if m["ects"])
    with_content = sum(1 for m in enriched if m["content"])
    with_outcomes = sum(1 for m in enriched if m["learning_outcomes"])
    unmapped_count = sum(1 for m in enriched if m.get("_unmapped_fields"))

    print(f"\n--- Normalization Stats ---")
    print(f"  Total modules: {len(enriched)}")
    print(f"  With ECTS: {with_ects}")
    print(f"  With content: {with_content}")
    print(f"  With learning outcomes: {with_outcomes}")
    print(f"  With unmapped fields: {unmapped_count}")

    if unmapped_count > 0:
        # Show which fields weren't mapped
        all_unmapped = set()
        for m in enriched:
            for key in m.get("_unmapped_fields", {}):
                all_unmapped.add(key)
        print(f"  Unmapped field names: {all_unmapped}")

    return enriched


def inspect_modules(modules: list[dict], count: int = 5):
    """Print random modules for manual quality inspection."""
    sample = random.sample(modules, min(count, len(modules)))
    print(f"\n=== Random Sample: {len(sample)} modules ===\n")

    for m in sample:
        print(f"─── Module {m['module_id']}: {m['module_name_raw']} ───")
        print(f"  ECTS:       {m['ects']}")
        print(f"  Semester:   {m['semester_offered']}")
        print(f"  Language:   {m['language']}")
        print(f"  Lecturer:   {m['lecturer']}")
        print(f"  Focus:      {m['focus_area']}")
        print(f"  Prereqs:    {m['prerequisites_formal']} (formal)")
        print(f"              {m['prerequisites_recommended']} (recommended)")
        print(f"  Content:    {m['content'][:150]}..." if len(m['content']) > 150 else f"  Content:    {m['content']}")
        print(f"  Assessment: {m['assessment'][:100]}..." if len(m['assessment']) > 100 else f"  Assessment: {m['assessment']}")

        if m.get("_unmapped_fields"):
            print(f"  ⚠ Unmapped: {list(m['_unmapped_fields'].keys())}")
        print()


def save_modules(modules: list[dict], output_path: str) -> None:
    """Write the module records as pretty-printed UTF-8 JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(modules, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(modules)} modules to {output_path}")
