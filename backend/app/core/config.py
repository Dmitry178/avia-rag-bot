"""Application configuration via pydantic-settings."""

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_ROOT.parent


class AppSettings(BaseModel):
    """
    Application-level settings.
    """

    title: str = "Avia Bot API"
    description: str = "RAG assistant for airport staff"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


class LogLevel(StrEnum):
    """
    Supported log levels.
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"
    CRITICAL = "CRITICAL"


class LogFormat(StrEnum):
    """
    Log output format.
    """

    JSON = "JSON"
    TEXT = "TEXT"


class DBSettings(BaseModel):
    """
    Database connection settings.
    """

    url: str = "sqlite:///./data/app.db"

    @property
    def async_url(self) -> str:
        """
        Return SQLAlchemy async URL (sqlite → sqlite+aiosqlite).
        """

        if self.url.startswith("sqlite+aiosqlite:"):
            return self.url

        if self.url.startswith("sqlite:///"):
            return self.url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

        if self.url.startswith("sqlite://"):
            return self.url.replace("sqlite://", "sqlite+aiosqlite://", 1)

        return self.url

    @staticmethod
    def _raw_sqlite_path(url: str) -> Path | None:
        for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
            if url.startswith(prefix):
                path = url.removeprefix(prefix)
                if path and not path.startswith(":"):
                    return Path(path)

        return None

    def sqlite_file_path(self, backend_root: Path) -> Path | None:
        """
        Return absolute filesystem path for file-based SQLite URLs.
        """

        raw_path = self._raw_sqlite_path(self.url)
        if raw_path is None:
            return None

        if raw_path.is_absolute():
            return raw_path

        return (backend_root / raw_path).resolve()

    def resolved_async_url(self, backend_root: Path) -> str:
        """
        Return async DB URL with an absolute SQLite path when applicable.
        """

        sqlite_path = self.sqlite_file_path(backend_root)
        if sqlite_path is None:
            return self.async_url

        return f"sqlite+aiosqlite:///{sqlite_path.as_posix()}"


class DataSettings(BaseModel):
    """
    Filesystem paths for SQLite and sidecar JSON artifacts.
    """

    dir: str = "./data"

    def resolve_dir(self, backend_root: Path) -> Path:
        """
        Return absolute data directory (relative paths are under backend root).
        """

        path = Path(self.dir)
        if path.is_absolute():
            return path

        return (backend_root / path).resolve()

    def ensure_exists(self, backend_root: Path) -> None:
        """
        Create data directory if missing.
        """

        self.resolve_dir(backend_root).mkdir(parents=True, exist_ok=True)


class FaissSettings(BaseModel):
    """
    FAISS vector index artifact directory (data-only, not a Python package).
    """

    dir: str = Field(default="./data", description="Directory for faiss.index (relative to backend root).")
    index_file: str = Field(default="faiss.index", description="FAISS index filename inside dir.")

    def index_path(self, backend_root: Path) -> Path:
        """
        Resolve absolute path to the FAISS index file.
        """

        base = Path(self.dir) if Path(self.dir).is_absolute() else backend_root / self.dir
        return base / self.index_file

    def ensure_exists(self, backend_root: Path) -> None:
        """
        Create FAISS artifact directory if missing.
        """

        self.index_path(backend_root).parent.mkdir(parents=True, exist_ok=True)


class ETLSettings(BaseModel):
    """
    ETL pipeline settings.
    """

    document_path: str = "data/rag-document.md"

    def resolve_document_path(self, backend_root: Path) -> Path:
        """
        Return absolute path to the knowledge base markdown document.
        """

        path = Path(self.document_path)
        if path.is_absolute():
            return path

        return backend_root / path


class LLMSettings(BaseModel):
    """
    OpenAI-compatible LLM provider settings.
    """

    base_url: str = ""
    api_key: str = ""
    model: str = ""
    summarization_model: str = ""
    embedding_model: str = ""


class LogSettings(BaseModel):
    """
    Structured logging settings.
    """

    name: str = "avia-bot-api"
    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.TEXT


class Settings(BaseSettings):
    """
    Root settings loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    log: LogSettings = Field(default_factory=LogSettings)
    db: DBSettings = Field(default_factory=DBSettings)
    data: DataSettings = Field(default_factory=DataSettings)
    faiss: FaissSettings = Field(default_factory=FaissSettings)
    etl: ETLSettings = Field(default_factory=ETLSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    @property
    def repo_root(self) -> Path:
        """
        Monorepo root directory.
        """

        return _REPO_ROOT

    @property
    def backend_root(self) -> Path:
        """
        Backend package root (backend/).
        """

        return _BACKEND_ROOT

    def resolve_data_dir(self) -> Path:
        """
        Absolute path to runtime artifacts (SQLite, FAISS, manifest sidecars).
        """

        return self.data.resolve_dir(self.backend_root)


settings = Settings()
