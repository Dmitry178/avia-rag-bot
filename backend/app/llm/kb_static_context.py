"""Load static knowledge-base sections for the RAG system prompt."""

from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from etl.chunking_schema import load_runtime_schema_for_language, resolve_schema_source_path
from etl.universal_chunker import UniversalChunker


@lru_cache(maxsize=8)
def load_kb_static_context(document_path: str, language_code: str = "ru") -> str:
    """
    Build the static knowledge-base policy block for the RAG system prompt.
    """

    path = Path(document_path)
    context = load_runtime_schema_for_language(language_code, str(settings.backend_root))
    schema = context.schema
    chunker = UniversalChunker(schema)
    source_path = resolve_schema_source_path(
        schema,
        schema_dir=context.schema_dir,
        backend_root=settings.backend_root,
        repo_root=settings.repo_root,
        source_override=str(path) if path.is_file() else None,
    )

    if not source_path.is_file():
        return ""

    text = source_path.read_text(encoding="utf-8")
    h1_blocks = chunker.split_h1_blocks(text)
    section_by_number: dict[str, str] = {}
    sections_by_category: dict[str, list[str]] = {}

    for block in h1_blocks:
        if block.section_number:
            section_by_number[block.section_number] = block.body.strip()
        category_id = chunker.classify_block(block)
        sections_by_category.setdefault(category_id, []).append(block.body.strip())

    parts = [
        "Knowledge-base static policies (always apply in RAG mode; not from retrieval):",
    ]

    if not schema.static_prompt.enabled:
        return ""

    for block in schema.static_prompt.blocks:
        source_sections = [section_by_number[number].strip() for number in block.source.section_numbers if number in section_by_number]
        if block.source.category_ids:
            for category_id in block.source.category_ids:
                source_sections.extend(item.strip() for item in sections_by_category.get(category_id, []))
        if not source_sections:
            continue

        merged_source = "\n\n".join(item for item in source_sections if item)
        if not merged_source:
            continue

        parts.append(
            f"\n### {block.title}\n{block.guidance_text}\n\n{merged_source}",
        )

    if len(parts) == 1:
        return ""

    return "\n".join(parts)
