"""Pytest configuration — keep tests off the development database."""

import asyncio
import os
import sys

import pytest

from pathlib import Path


_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_TEST_DB_PATH = (Path(__file__).resolve().parent / ".pytest_app.db").resolve()
_TEST_DB_URL = f"sqlite+aiosqlite:///{_TEST_DB_PATH.as_posix()}"
_PARITY_BACKEND_DB = (_BACKEND_ROOT / "data" / "app.db").resolve()


def _is_parity_run() -> bool:
    return "--run-parity" in sys.argv


def _configure_test_database() -> None:
    """
    Point the application at an isolated SQLite file for the test session.
    """

    if _is_parity_run():
        os.environ["RUN_PARITY_TESTS"] = "1"
        os.environ["DB__URL"] = f"sqlite+aiosqlite:///{_PARITY_BACKEND_DB.as_posix()}"
        return

    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()

    os.environ["DB__URL"] = _TEST_DB_URL


_configure_test_database()


def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Register opt-in flags for integration suites.
    """

    parser.addoption(
        "--run-parity",
        action="store_true",
        default=False,
        help="Run embed vs mcp-rag parity tests (requires KB indexes and LLM__* env).",
    )


def pytest_configure(config: pytest.Config) -> None:
    """
    Re-apply DB isolation before test modules import the application.
    """

    _configure_test_database()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """
    Skip parity tests unless explicitly requested.
    """

    if config.getoption("--run-parity"):
        return

    skip_parity = pytest.mark.skip(reason="parity tests skipped; pass --run-parity to enable")
    for item in items:
        if "parity" in item.keywords:
            item.add_marker(skip_parity)


@pytest.fixture(scope="session", autouse=True)
def _assert_isolated_test_database() -> None:
    """
    Fail fast when pytest accidentally binds to the development database.
    """

    if os.environ.get("RUN_PARITY_TESTS") == "1":
        yield
        return

    from app.db.session import get_engine

    db_url = get_engine().url.render_as_string(hide_password=False)
    expected = _TEST_DB_PATH.as_posix()
    assert expected in db_url, f"Tests must use isolated database {_TEST_DB_PATH}, got {db_url}"

    yield


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_database() -> None:
    """
    Dispose the engine and remove the isolated test database after the session.
    """

    yield

    from app.db.session import dispose_engine

    asyncio.run(dispose_engine())

    if os.environ.get("RUN_PARITY_TESTS") == "1":
        return

    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()
