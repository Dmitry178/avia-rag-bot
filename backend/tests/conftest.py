"""Pytest configuration — keep tests off the development database."""

import os
import pytest

from pathlib import Path


_TEST_DB_PATH = (Path(__file__).resolve().parent / ".pytest_app.db").resolve()

if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()

os.environ["DB__URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH.as_posix()}"


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_database() -> None:
    """
    Remove the isolated test database after the session.
    """

    yield

    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()
