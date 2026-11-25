"""Typed project settings, read from environment variables and the project's .env file.

Every value can be overridden by an environment variable with the same name in
upper case (e.g. GEMINI_FAST_MODEL). Relative paths are resolved against the
project root, so commands work from any working directory.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# src/student_path/settings.py -> project root (the package is installed in editable mode)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # "KEY=" in .env counts as unset
        extra="ignore",
        validate_default=True,  # so default paths are resolved too
    )

    # LLM (Gemini). Pin exact model versions for reproducible evals; aliases drift.
    google_api_key: SecretStr | None = None
    gemini_fast_model: str | None = None  # routing, extraction, normalization
    gemini_smart_model: str | None = None  # plan explanations, harder reasoning

    # Data
    data_dir: Path = Path("data")
    pdf_path: Path = Path("data/source/Modulkatalog-Master-Informatik.pdf")

    # Vector store: embedded mode uses qdrant_path; set qdrant_url to use a server instead
    qdrant_path: Path = Path("data/qdrant")
    qdrant_url: str | None = None
    qdrant_collection: str = "modules"
    embedding_model: str = "BAAI/bge-m3"

    @field_validator("data_dir", "pdf_path", "qdrant_path")
    @classmethod
    def _resolve_against_root(cls, value: Path) -> Path:
        return value if value.is_absolute() else PROJECT_ROOT / value

    @property
    def legacy_dir(self) -> Path:
        """Outputs of the superseded v1 pipeline (Docling OCR run, regex-normalized modules.json)."""
        return self.data_dir / "legacy"


@lru_cache
def get_settings() -> Settings:
    """Settings are read once per process; tests can call get_settings.cache_clear()."""
    return Settings()
