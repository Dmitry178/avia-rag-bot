"""Verify backend starts without the optional mcp-rag (rag) extra installed."""

import subprocess
import sys


def test_backend_imports_without_mcp_rag(monkeypatch) -> None:
    """
    Core FastAPI app modules should import when ``src`` (mcp-rag) is unavailable.
    """

    code = """
import sys

class _BlockSrc:
    def find_module(self, name, path=None):
        if name == "src" or name.startswith("src."):
            return self
        return None

    def load_module(self, name):
        raise ImportError(f"blocked for test: {name}")

sys.meta_path.insert(0, _BlockSrc())

from app.main import create_app

app = create_app()
assert app is not None
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(__import__("pathlib").Path(__file__).resolve().parents[1]),
    )

    assert result.returncode == 0, result.stderr
