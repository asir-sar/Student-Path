"""Qdrant client factory: one place that decides between embedded and server mode."""

from qdrant_client import QdrantClient

from student_path.settings import Settings, get_settings


def get_qdrant_client(settings: Settings | None = None) -> QdrantClient:
    """Return a Qdrant client for the configured mode.

    - Server mode when QDRANT_URL is set (e.g. the docker-compose service).
    - Embedded mode otherwise: data lives in files under QDRANT_PATH. Only one
      process can open an embedded store at a time, so stop the API before
      running indexing jobs against the same path.
    """
    s = settings or get_settings()
    if s.qdrant_url:
        return QdrantClient(url=s.qdrant_url, timeout=10)
    s.qdrant_path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(s.qdrant_path))
