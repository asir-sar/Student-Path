"""Command-line interface: `uv run sp --help`.

Heavy libraries (Docling, torch) are imported inside the commands that need them,
so `sp --help` and `sp config` stay fast.
"""

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
