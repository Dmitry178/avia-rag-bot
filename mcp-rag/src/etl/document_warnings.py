"""Non-fatal document structure warnings for schema-driven ETL."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol

from src.etl.universal_chunker import HeadingBlock, UniversalChunker


class SupportsEtlWarningLog(Protocol):
    """
    Minimal logger surface for ETL document warnings.
    """

    def warning(self, event: str, **fields: object) -> None:
        """
        Emit a structured warning event.
        """


@dataclass(frozen=True, slots=True)
class DuplicateSectionNumberWarning:
    """
    Duplicate parsed H1 section number with all matching titles.
    """

    section_number: str
    titles: tuple[str, ...]


def collect_duplicate_section_number_warnings(
    blocks: list[HeadingBlock],
) -> list[DuplicateSectionNumberWarning]:
    """
    Find H1 blocks that share the same parsed section number.

    Processing continues as usual; this is advisory only.
    """

    titles_by_number: dict[str, list[str]] = defaultdict(list)

    for block in blocks:
        if block.section_number is None:
            continue
        titles_by_number[block.section_number].append(block.title)

    return [
        DuplicateSectionNumberWarning(section_number=section_number, titles=tuple(titles))
        for section_number, titles in sorted(titles_by_number.items())
        if len(titles) > 1
    ]


def emit_duplicate_section_number_warnings(
    chunker: UniversalChunker,
    text: str,
    *,
    source_path: str,
    logger: SupportsEtlWarningLog,
) -> list[DuplicateSectionNumberWarning]:
    """
    Log duplicate section-number warnings for one source document.
    """

    warnings = collect_duplicate_section_number_warnings(chunker.split_h1_blocks(text))

    for item in warnings:
        logger.warning(
            "duplicate_section_numbers_in_document",
            source_path=source_path,
            section_number=item.section_number,
            titles=list(item.titles),
            title_count=len(item.titles),
        )

    return warnings
