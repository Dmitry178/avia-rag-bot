"""Pytest configuration — keep tests off the development database."""

import asyncio
import os
import pytest

from pathlib import Path


_TEST_DB_PATH = (Path(__file__).resolve().parent / ".pytest_app.db").resolve()
_TEST_DB_URL = f"sqlite+aiosqlite:///{_TEST_DB_PATH.as_posix()}"


def _configure_test_database() -> None:
    """
    Point the application at an isolated SQLite file for the test session.
    """

    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()

    os.environ["DB__URL"] = _TEST_DB_URL


_configure_test_database()


def pytest_configure(config: pytest.Config) -> None:
    """
    Re-apply DB isolation before test modules import the application.
    """

    _configure_test_database()


@pytest.fixture(scope="session", autouse=True)
def _assert_isolated_test_database() -> None:
    """
    Fail fast when pytest accidentally binds to the development database.
    """

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

    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()
