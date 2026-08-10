"""Unit tests for non-fatal ETL document warnings."""

from etl.chunking_schema import load_runtime_schema_for_language
from etl.document_warnings import (
    collect_duplicate_section_number_warnings,
    emit_duplicate_section_number_warnings,
)
from etl.universal_chunker import HeadingBlock, UniversalChunker

from tests.paths import BACKEND_ROOT


class _RecordingLogger:
    """
    Capture structured warning events for assertions.
    """

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def warning(self, event: str, **fields: object) -> None:
        self.events.append((event, fields))


def test_collect_duplicate_section_number_warnings() -> None:
    """
    Duplicate parsed H1 numbers should be reported with all titles.
    """

    blocks = [
        HeadingBlock(title="13. First section", body="", index=0, section_number="13"),
        HeadingBlock(title="13. Second section", body="", index=1, section_number="13"),
        HeadingBlock(title="14. Unique section", body="", index=2, section_number="14"),
    ]

    warnings = collect_duplicate_section_number_warnings(blocks)

    assert len(warnings) == 1
    assert warnings[0].section_number == "13"
    assert warnings[0].titles == ("13. First section", "13. Second section")


def test_emit_duplicate_section_number_warnings_logs_but_does_not_block_chunking() -> None:
    """
    Warnings should be logged while chunking still produces output.
    """

    context = load_runtime_schema_for_language("ru", str(BACKEND_ROOT))
    chunker = UniversalChunker(context.schema)
    text = (
        "# 13. Duplicate A\n\nBody A.\n\n"
        "# 13. Duplicate B\n\nBody B.\n\n"
        "# 99. Unique\n\nBody unique.\n"
    )
    logger = _RecordingLogger()

    warnings = emit_duplicate_section_number_warnings(
        chunker,
        text,
        source_path="synthetic.md",
        logger=logger,
    )
    chunks = chunker.chunk_document(text, source_path="synthetic.md")

    assert len(warnings) == 1
    assert logger.events
    assert logger.events[0][0] == "duplicate_section_numbers_in_document"
    assert logger.events[0][1]["section_number"] == "13"
    assert chunks
