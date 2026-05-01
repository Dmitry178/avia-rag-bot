"""Parse rag-document.md into a DocumentNode tree."""

import re

from etl.types import ContentType, DocumentNode

# Headings by level only: one #, two ##, three ### (not ####).
_H1_RE = re.compile(r"^# (?P<title>.+)$", re.MULTILINE)
_H2_RE = re.compile(r"^## (?P<title>.+)$", re.MULTILINE)
_H3_RE = re.compile(r"^### (?P<title>.+)$", re.MULTILINE)
# Section number from H1 title, e.g. "03. Регистрация" → "03".
_SECTION_NUM_RE = re.compile(r"^(\d{2})\.\s*")


def _section_number(title: str) -> str | None:
    match = _SECTION_NUM_RE.match(title.strip())
    return match.group(1) if match else None


def _content_type_for_section(title: str) -> ContentType:
    """
    Classify section by H1 number and keywords.
    Sections 01–12 without special markers are treated as SOP.
    """
    
    number = _section_number(title)
    lowered = title.lower()

    if number == "00":
        return ContentType.META

    if number == "13" or "out of scope" in lowered:
        return ContentType.OUT_OF_SCOPE

    if number == "14" or title.startswith("14.") or "faq" in lowered:
        return ContentType.FAQ

    if number == "15" or "глоссарий" in lowered:
        return ContentType.GLOSSARY

    if number == "16" or "decision tree" in lowered:
        return ContentType.DECISION_TREE

    if number == "17" or "практические сценарии" in lowered:
        return ContentType.SCENARIO

    return ContentType.SOP


def _split_h1_sections(text: str) -> list[tuple[str, str]]:
    """
    Split document into blocks between consecutive # headings.
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


def _split_by_heading(body: str, pattern: re.Pattern[str]) -> list[tuple[str, str]]:
    """
    Split section body by subheadings (## or ###).
    Returns (title, text until next heading of the same level) pairs.
    """
    
    matches = list(pattern.finditer(body))
    if not matches:
        # No subheadings — treat entire body as one block with empty title.
        return [("", body.strip())] if body.strip() else []

    parts: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        title = match.group("title").strip()
        content = body[start:end].strip()
        parts.append((title, content))

    return parts


def _make_node_id(section_num: str | None, *parts: str) -> str:
    """
    Stable node id: section number + slug of path segments in the tree.
    """
    
    slug_parts = [section_num or "xx", *parts]
    return ".".join(part.strip().lower().replace(" ", "_")[:40] for part in slug_parts if part)


def parse_markdown(text: str, source_path: str = "") -> list[DocumentNode]:
    """
    Parse markdown into a flat list of DocumentNode records grouped by headings.
    """

    nodes: list[DocumentNode] = []

    for section_title, section_body in _split_h1_sections(text):
        section_num = _section_number(section_title)
        section_type = _content_type_for_section(section_title)
        section_id = _make_node_id(section_num, "root")

        # Special sections (FAQ, glossary, …) stay as one H1 block here;
        # the chunker applies type-specific splitting later.
        if section_type in {
            ContentType.META,
            ContentType.OUT_OF_SCOPE,
            ContentType.FAQ,
            ContentType.GLOSSARY,
            ContentType.DECISION_TREE,
            ContentType.SCENARIO,
        }:
            nodes.append(
                DocumentNode(
                    id=section_id,
                    section=section_title,
                    title=section_title,
                    level=1,
                    content_type=section_type,
                    text=section_body,
                    parent_id=None,
                    metadata={"source_path": source_path},
                )
            )
            continue

        # SOP: expand ## → ### tree.
        h2_parts = _split_by_heading(section_body, _H2_RE)
        if not h2_parts or (len(h2_parts) == 1 and h2_parts[0][0] == ""):
            # No ## inside section — single node for the whole H1.
            nodes.append(
                DocumentNode(
                    id=section_id,
                    section=section_title,
                    title=section_title,
                    level=1,
                    content_type=section_type,
                    text=section_body,
                    parent_id=None,
                    metadata={"source_path": source_path},
                )
            )
            continue

        for h2_title, h2_body in h2_parts:
            if not h2_title and not h2_body:
                continue

            h2_id = _make_node_id(section_num, h2_title or "section")
            nodes.append(
                DocumentNode(
                    id=h2_id,
                    section=section_title,
                    title=h2_title or section_title,
                    level=2,
                    content_type=section_type,
                    text=h2_body,
                    parent_id=section_id,
                    metadata={"source_path": source_path},
                )
            )

            # H3 nodes preserve hierarchy; SOP chunker splits H2 by ### itself
            # and chunk_node skips level=3 nodes to avoid duplicate chunks.
            for h3_title, h3_body in _split_by_heading(h2_body, _H3_RE):
                if not h3_title:
                    continue

                nodes.append(
                    DocumentNode(
                        id=_make_node_id(section_num, h2_title, h3_title),
                        section=section_title,
                        title=h3_title,
                        level=3,
                        content_type=section_type,
                        text=h3_body,
                        parent_id=h2_id,
                        metadata={"source_path": source_path},
                    )
                )

    return nodes
