"""Command-line interface: `uv run sp --help`.

Heavy libraries (Docling, torch) are imported inside the commands that need them,
so `sp --help` and `sp config` stay fast.
"""

import json
from pathlib import Path
from typing import Annotated

import typer

from student_path import __version__
from student_path.settings import get_settings

app = typer.Typer(
    help="Student-Path: RAG chatbot and semester planner for the module catalogue.",
    no_args_is_help=True,
)
legacy_app = typer.Typer(
    help="Superseded v1 pipeline, kept only as the experiment E1 baseline. Outputs go to data/legacy/.",
    no_args_is_help=True,
)
app.add_typer(legacy_app, name="legacy")
ingest_app = typer.Typer(
    help="v2 ingestion pipeline (phase P1): PDF -> module records.", no_args_is_help=True
)
app.add_typer(ingest_app, name="ingest")


def _print_version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_print_version, is_eager=True, help="Show the version and exit."),
    ] = False,
) -> None:
    """Student-Path command-line tools."""


@app.command()
def config() -> None:
    """Show the effective settings (secrets are never printed)."""
    settings = get_settings()
    for name, value in settings.model_dump().items():
        if name.endswith("_key"):
            shown = "set" if value is not None else "not set"
        else:
            shown = "not set" if value is None else str(value)
        typer.echo(f"{name:20s} {shown}")


@app.command()
def check() -> None:
    """Check that the environment is ready: source PDF, Gemini settings, Qdrant.

    Exits with code 1 if a required check fails. Gemini settings are only warnings
    until the LLM steps start (phase P1.8).
    """
    settings = get_settings()
    failed = False

    def report(ok: bool | None, label: str, detail: str) -> None:
        mark = {True: "ok  ", False: "FAIL", None: "warn"}[ok]
        typer.echo(f"[{mark}] {label:18s} {detail}")

    if settings.pdf_path.exists():
        size_mb = settings.pdf_path.stat().st_size / 1_048_576
        report(True, "source PDF", f"{settings.pdf_path.name} ({size_mb:.1f} MB)")
    else:
        failed = True
        report(False, "source PDF", f"missing: {settings.pdf_path}")

    report(
        True if settings.google_api_key else None,
        "GOOGLE_API_KEY",
        "set" if settings.google_api_key else "not set (needed from P1.8)",
    )
    for name in ("gemini_fast_model", "gemini_smart_model"):
        value = getattr(settings, name)
        report(True if value else None, name.upper(), value or "not set (pin an exact model id)")

    from student_path.store.qdrant import get_qdrant_client

    mode = f"server {settings.qdrant_url}" if settings.qdrant_url else f"embedded {settings.qdrant_path}"
    try:
        client = get_qdrant_client(settings)
        names = [c.name for c in client.get_collections().collections]
        client.close()
        report(True, "Qdrant", f"{mode}, {len(names)} collection(s)")
    except Exception as exc:  # report every connection problem the same way
        failed = True
        hint = " (is `docker compose up -d` running?)" if settings.qdrant_url else ""
        report(False, "Qdrant", f"{mode}: {type(exc).__name__}{hint}")

    if failed:
        raise typer.Exit(code=1)


def _parse_pages(pages: str | None) -> tuple[int, int] | None:
    if pages is None:
        return None
    try:
        first, last = (int(p) for p in pages.split("-", 1))
    except ValueError:
        raise typer.BadParameter("use FIRST-LAST, e.g. 1-10") from None
    if not 1 <= first <= last:
        raise typer.BadParameter("pages are 1-based and FIRST must not exceed LAST")
    return first, last


@legacy_app.command("parse")
def legacy_parse(
    pdf: Annotated[Path | None, typer.Option(help="PDF to parse [default: settings.pdf_path]")] = None,
    output_dir: Annotated[Path | None, typer.Option(help="Output directory [default: data/legacy]")] = None,
    pages: Annotated[str | None, typer.Option(help="Page range, 1-based and inclusive, e.g. 1-10")] = None,
    inspect: Annotated[bool, typer.Option(help="Print sample table blocks afterwards")] = False,
) -> None:
    """v1: parse the PDF with Docling (OCR on), export Markdown + JSON."""
    page_range = _parse_pages(pages)
    settings = get_settings()
    pdf = pdf or settings.pdf_path
    output_dir = output_dir or settings.legacy_dir
    if not pdf.exists():
        raise typer.BadParameter(f"PDF not found: {pdf}", param_hint="--pdf")

    from student_path.legacy.parser import parse_pdf, quick_inspect

    parse_pdf(str(pdf), str(output_dir), page_range)
    if inspect:
        quick_inspect(str(output_dir))


@legacy_app.command("normalize")
def legacy_normalize(
    input_path: Annotated[
        Path | None,
        typer.Option(
            "--input", help="Docling output, Markdown or JSON [default: data/legacy/modulkatalog_raw.md]"
        ),
    ] = None,
    fmt: Annotated[str, typer.Option("--format", help="auto, markdown or json")] = "auto",
    output: Annotated[
        Path | None, typer.Option(help="Output JSON [default: data/legacy/modules.json]")
    ] = None,
    inspect: Annotated[bool, typer.Option(help="Print random modules afterwards")] = False,
    inspect_count: Annotated[int, typer.Option(help="How many modules to print")] = 5,
) -> None:
    """v1: regex-normalize the Markdown tables (known to be ~47% complete, see findings F5/F6)."""
    if fmt not in ("auto", "markdown", "json"):
        raise typer.BadParameter("choose auto, markdown or json", param_hint="--format")
    settings = get_settings()
    input_path = input_path or settings.legacy_dir / "modulkatalog_raw.md"
    output = output or settings.legacy_dir / "modules.json"
    if not input_path.exists():
        raise typer.BadParameter(
            f"input not found: {input_path} (run `sp legacy parse` first)", param_hint="--input"
        )

    from student_path.legacy.normalizer import inspect_modules, normalize_modules, save_modules

    modules = normalize_modules(str(input_path), fmt)
    save_modules(modules, str(output))
    if inspect:
        inspect_modules(modules, inspect_count)


@ingest_app.command("probe")
def ingest_probe() -> None:
    """P1.1: describe the source PDF (checksum, pages, text layer, version, bookmarks) in a manifest."""
    from student_path.ingestion.probe import probe, write_manifest

    settings = get_settings()
    manifest = probe(settings.pdf_path)
    out = settings.processed_dir / "manifest.json"
    write_manifest(manifest, out)
    typer.echo(f"{manifest.pdf_name}: {manifest.pages} pages, version {manifest.catalogue_version}")
    typer.echo(f"  sha256 {manifest.pdf_sha256}")
    typer.echo(f"  pages without text layer: {len(manifest.pages_without_text)}")
    typer.echo(f"  bookmarks: {manifest.bookmarks}, with exam number (modules): {manifest.module_bookmarks}")
    typer.echo(f"Saved {out}")


@ingest_app.command("extract")
def ingest_extract(
    pages: Annotated[str | None, typer.Option(help="Page range, 1-based and inclusive, e.g. 49-51")] = None,
    threads: Annotated[int, typer.Option(help="CPU threads for Docling's models")] = 8,
    force: Annotated[bool, typer.Option(help="Re-run even if the cached output exists")] = False,
) -> None:
    """P1.2: run Docling (OCR off, TableFormer ACCURATE) and cache the DoclingDocument JSON."""
    page_range = _parse_pages(pages)
    settings = get_settings()
    name = "docling.json" if page_range is None else f"docling_p{page_range[0]}-{page_range[1]}.json"
    out = settings.interim_dir / name
    if out.exists() and not force:
        typer.echo(f"Cached: {out} (use --force to re-run)")
        return

    from student_path.ingestion.extract import extract

    typer.echo(f"Running Docling on {settings.pdf_path.name} ({pages or 'all pages'}) ...")
    stats = extract(settings.pdf_path, out, page_range=page_range, num_threads=threads)
    typer.echo(
        f"Done in {stats.seconds:.0f} s: {stats.pages_converted} pages, {stats.tables} tables, "
        f"{stats.texts} text items (docling {stats.docling_version})"
    )
    typer.echo(f"Saved {out}")


@ingest_app.command("segment")
def ingest_segment() -> None:
    """P1.3: split the catalogue into 201 module page ranges using the PDF bookmarks."""
    from student_path.ingestion.segment import segment_modules, write_segments

    settings = get_settings()
    segments = segment_modules(settings.pdf_path)
    out = settings.interim_dir / "segments.jsonl"
    write_segments(segments, out)
    no_id = sum(1 for s in segments if s.module_id is None)
    first, last = segments[0].page_start, segments[-1].page_end
    typer.echo(f"{len(segments)} modules, pages {first}-{last}, {no_id} without a module ID")
    typer.echo(f"Saved {out}")


@ingest_app.command("coverage")
def ingest_coverage(
    doc: Annotated[
        Path | None, typer.Option(help="DoclingDocument JSON [default: data/interim/docling.json]")
    ] = None,
    threshold: Annotated[float, typer.Option(help="Pages below this share are listed")] = 0.99,
    show: Annotated[int, typer.Option(help="How many of the weakest pages to print")] = 15,
) -> None:
    """P1.2 gate: share of the PDF's text layer that survives in the Docling output, per page."""
    from student_path.ingestion.coverage import text_coverage

    settings = get_settings()
    doc = doc or settings.interim_dir / "docling.json"
    if not doc.exists():
        raise typer.BadParameter(f"not found: {doc} (run `sp ingest extract` first)", param_hint="--doc")
    pages = text_coverage(settings.pdf_path, doc)
    words = sum(p.pdf_words for p in pages)
    overall = sum(p.pdf_words * p.covered for p in pages) / words if words else 1.0
    weak = sorted((p for p in pages if p.covered < threshold), key=lambda p: p.covered)
    out = settings.processed_dir / f"coverage_{doc.stem}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"doc": doc.name, "overall": overall, "pages": len(pages), "below_threshold": len(weak),
             "threshold": threshold, "per_page": [p.model_dump() for p in pages]},
            indent=1,
        ) + "\n",
        encoding="utf-8",
    )  # fmt: skip
    typer.echo(f"{doc.name}: {overall:.2%} of {words} text-layer words covered over {len(pages)} pages")
    typer.echo(f"pages below {threshold:.0%}: {len(weak)}")
    for p in weak[:show]:
        typer.echo(f"  p.{p.page:>3} {p.covered:6.1%}  missing e.g. {', '.join(p.missing_sample[:6])}")
    typer.echo(f"Saved {out}")
