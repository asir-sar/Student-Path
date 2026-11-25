from typer.testing import CliRunner

from student_path.cli import app
from student_path.settings import Settings, get_settings
from student_path.store.qdrant import get_qdrant_client

runner = CliRunner()


def test_embedded_client_uses_qdrant_path(tmp_path):
    settings = Settings(qdrant_path=tmp_path / "qdrant", qdrant_url=None)
    client = get_qdrant_client(settings)
    assert client.get_collections().collections == []
    client.close()
    assert (tmp_path / "qdrant").is_dir()


def test_check_passes_in_embedded_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("QDRANT_PATH", str(tmp_path / "qdrant"))
    monkeypatch.delenv("QDRANT_URL", raising=False)
    get_settings.cache_clear()
    result = runner.invoke(app, ["check"])
    get_settings.cache_clear()
    assert result.exit_code == 0, result.stdout
    assert "[ok  ] Qdrant" in result.stdout


def test_check_fails_when_server_unreachable(monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "http://127.0.0.1:1")  # nothing listens on port 1
    get_settings.cache_clear()
    result = runner.invoke(app, ["check"])
    get_settings.cache_clear()
    assert result.exit_code == 1
    assert "[FAIL] Qdrant" in result.stdout
