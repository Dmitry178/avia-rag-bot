"""Application configuration for mcp-rag (repo-root ``data/`` volume)."""

import os

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.exceptions.service import ServiceError

_MCP_RAG_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _MCP_RAG_ROOT.parent

DEFAULT_KB_LANGUAGE = "en"


class KbLanguageEntry(BaseModel):
    """
    Static knowledge-base language: code, markdown source path, display label.
    """

    code: str = Field(description="Language code used in DB columns and API (e.g. ru, en).")
    document_path: str = Field(
        description="Path to the markdown KB file (relative to repo root or absolute).",
    )
    display_name: str = Field(description="Human-readable language label for logs and docs.")
    etl_schema_path: str | None = Field(
        default=None,
        description=(
            "Optional path to ETL chunking schema JSON (relative to repo root). "
            "Defaults to data/chunking-schema-{code}.json."
        ),
    )


KB_LANGUAGES: dict[str, KbLanguageEntry] = {
    "ru": KbLanguageEntry(
        code="ru",
        document_path="data/rag-document-ru.md",
        display_name="Русский",
        etl_schema_path="data/chunking-schema-ru.json",
    ),
    "en": KbLanguageEntry(
        code="en",
        document_path="data/rag-document-en.md",
        display_name="English",
        etl_schema_path="data/chunking-schema-en.json",
    ),
}


def list_kb_language_codes() -> list[str]:
    """
    Return supported KB language codes in stable order.
    """

    return list(KB_LANGUAGES.keys())


def get_kb_language(language_code: str) -> KbLanguageEntry:
    """
    Return a language definition or raise when the code is unknown.
    """

    language = KB_LANGUAGES.get(language_code)
    if language is None:
        raise ServiceError(
            detail=f"Unknown knowledge-base language: {language_code}",
            error_code="kb_language_unknown",
            status_code=404,
        )

    return language


def resolve_kb_document_path(language_code: str, backend_root: Path) -> Path:
    """
    Return absolute path to the markdown document for a KB language.
    """

    language = get_kb_language(language_code)
    path = Path(language.document_path)

    if path.is_absolute():
        return path

    return backend_root / path


def resolve_kb_chunking_schema_path(language_code: str, backend_root: Path) -> Path:
    """
    Return absolute path to the schema-driven ETL chunking JSON for a KB language.
    """

    language = get_kb_language(language_code)
    if language.etl_schema_path is not None:
        path = Path(language.etl_schema_path)
        return path if path.is_absolute() else backend_root / path

    return backend_root / "data" / f"chunking-schema-{language_code}.json"


class AppSettings(BaseModel):
    """
    Application-level settings.
    """

    title: str = "mcp-rag"
    description: str = "MCP server for RAG retrieval and ETL"


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

    url: str = "sqlite:///./data/kb.db"

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
        Return absolute data directory (relative paths are under repo root).
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
    FAISS vector index artifact directory.
    """

    dir: str = Field(default="./data", description="Directory for per-language FAISS indexes (relative to repo root).")
    index_file: str = Field(
        default="faiss-{language_code}.index",
        description="FAISS index filename pattern; {language_code} is replaced per KB language.",
    )

    def index_path(self, backend_root: Path, language_code: str) -> Path:
        """
        Resolve absolute path to the FAISS index file for a language.
        """

        base = Path(self.dir) if Path(self.dir).is_absolute() else backend_root / self.dir
        filename = self.index_file.format(language_code=language_code)

        return base / filename

    def ensure_exists(self, backend_root: Path) -> None:
        """
        Create FAISS artifact directory if missing.
        """

        base = Path(self.dir) if Path(self.dir).is_absolute() else backend_root / self.dir
        base.mkdir(parents=True, exist_ok=True)


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

    name: str = "mcp-rag"
    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.TEXT


class Settings(BaseSettings):
    """
    Root settings loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=str(_MCP_RAG_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    log: LogSettings = Field(default_factory=LogSettings)
    db: DBSettings = Field(default_factory=DBSettings)
    data: DataSettings = Field(default_factory=DataSettings)
    faiss: FaissSettings = Field(default_factory=FaissSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    @model_validator(mode="before")
    @classmethod
    def apply_mcp_rag_db_url_alias(cls, data: Any) -> Any:
        """
        Allow KB SQLite URL via ``MCP_RAG__DB__URL`` / ``MCP_RAG__DB_URL`` without clashing with backend ``DB__URL``.
        """

        mcp_db_url = os.environ.get("MCP_RAG__DB__URL") or os.environ.get("MCP_RAG__DB_URL")
        if not mcp_db_url:
            return data

        payload = dict(data) if isinstance(data, dict) else {}
        db_settings = payload.get("db")
        if isinstance(db_settings, dict):
            payload["db"] = {**db_settings, "url": mcp_db_url}
        else:
            payload["db"] = {"url": mcp_db_url}

        return payload

    @property
    def repo_root(self) -> Path:
        """
        Monorepo root directory.
        """

        return _REPO_ROOT

    @property
    def backend_root(self) -> Path:
        """
        Path anchor for KB-relative paths (repo root; ``data/`` is underneath).
        """

        return _REPO_ROOT

    @property
    def data_root(self) -> Path:
        """
        Absolute path to the MCP KB volume (``<repo>/data``).
        """

        return self.resolve_data_dir()

    def resolve_data_dir(self) -> Path:
        """
        Absolute path to runtime artifacts (SQLite, FAISS, manifest sidecars).
        """

        return self.data.resolve_dir(self.backend_root)


settings = Settings()
