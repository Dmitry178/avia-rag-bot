"""Extract non-indexed H1 sections for the RAG system prompt."""

import re

_H1_RE = re.compile(r"^# (?P<title>.+)$", re.MULTILINE)
_SECTION_NUM_RE = re.compile(r"^(\d{2})\.\s*")


def _split_h1_sections(text: str) -> list[tuple[str, str]]:
    """
    Split markdown into (H1 title, body) pairs.
    """

    matches = list(_H1_RE.finditer(text))
    if not matches:
        return []

    sections: list[tuple[str, str]] = []

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        title = match.group("title").strip()
        body = text[match.end() : end].strip()
        sections.append((title, body))

    return sections


def _section_number(title: str) -> str | None:
    match = _SECTION_NUM_RE.match(title.strip())
    return match.group(1) if match else None


def extract_static_prompt_sections(text: str) -> dict[str, str]:
    """
    Return full bodies of chapters indexed for the system prompt (00 and 13).
    """

    sections: dict[str, str] = {}

    for title, body in _split_h1_sections(text):
        number = _section_number(title)
        if number in {"00", "13"} and body:
            sections[number] = body

    return sections
