"""Load static knowledge-base sections for the RAG system prompt."""

from functools import lru_cache
from pathlib import Path

from etl.static_sections import extract_static_prompt_sections

_CHAPTER_00_GUIDANCE = (
    "Chapter 00 describes the assistant's purpose, capabilities, limitations, and how staff "
    "should use it. Apply these policies when interpreting user requests."
)

_CHAPTER_13_GUIDANCE = (
    "Chapter 13 defines in-scope and out-of-scope topics and how to refuse or redirect. "
    "When the user's question is out of scope, refuse politely using these rules even if "
    "retrieved excerpts seem related."
)


@lru_cache(maxsize=4)
def load_kb_static_context(document_path: str) -> str:
    """
    Build the static knowledge-base policy block for the RAG system prompt.
    """

    path = Path(document_path)
    if not path.is_file():
        return ""

    sections = extract_static_prompt_sections(path.read_text(encoding="utf-8"))
    meta = sections.get("00", "").strip()
    out_of_scope = sections.get("13", "").strip()

    if not meta and not out_of_scope:
        return ""

    parts = [
        "Knowledge-base static policies (always apply in RAG mode; not from retrieval):",
    ]

    if meta:
        parts.append(
            f"\n### Chapter 00 — Project description\n{_CHAPTER_00_GUIDANCE}\n\n{meta}",
        )

    if out_of_scope:
        parts.append(
            f"\n### Chapter 13 — Out of Scope\n{_CHAPTER_13_GUIDANCE}\n\n{out_of_scope}",
        )

    return "\n".join(parts)
