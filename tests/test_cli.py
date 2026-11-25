import pytest
import typer
from typer.testing import CliRunner

from student_path import __version__
from student_path.cli import _parse_pages, app
from student_path.settings import PROJECT_ROOT, Settings, get_settings

runner = CliRunner()


@pytest.fixture(autouse=True)
def fresh_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_config_never_prints_secrets(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "super-secret-value")
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "super-secret-value" not in result.stdout
    assert "google_api_key" in result.stdout and "set" in result.stdout


def test_relative_paths_resolve_against_project_root(monkeypatch):
    monkeypatch.setenv("DATA_DIR", "data")
    settings = Settings()
    assert settings.data_dir == PROJECT_ROOT / "data"
    assert settings.pdf_path.is_relative_to(PROJECT_ROOT)


def test_default_pdf_exists():
    assert get_settings().pdf_path.exists()


@pytest.mark.parametrize("raw, expected", [(None, None), ("1-10", (1, 10)), ("5-5", (5, 5))])
def test_parse_pages_valid(raw, expected):
    assert _parse_pages(raw) == expected


@pytest.mark.parametrize("raw", ["0-10", "10-1", "abc", "3"])
def test_parse_pages_invalid(raw):
    with pytest.raises(typer.BadParameter):
        _parse_pages(raw)
