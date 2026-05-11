"""Turn parsed document nodes into retrieval chunks."""

import re

from etl.parser import parse_markdown
from etl.hashing import content_hash
from etl.types import ChunkDraft, ContentType, DocumentNode

# Matches **Вопрос:**/**Ответ:** and list variant: * **Вопрос:**
_FAQ_PAIR_RE = re.compile(
    r"(?:^|\n)\s*(?:\*\s+)?\*\*Вопрос:\*\*\s*(?P<question>.+?)\s*\n\s*(?:\*\s+)?\*\*Ответ:\*\*\s*(?P<answer>.+?)(?=\n\s*(?:\*\s+)?\*\*Вопрос:\*\*|\Z)",
    re.DOTALL,
)
_GLOSSARY_TERM_RE = re.compile(r"^\*\*(?P<term>.+?):\*\*\s*(?P<definition>.+)$", re.MULTILINE)
_SCENARIO_RE = re.compile(r"^## (Сценарий \d+:.+)$", re.MULTILINE)
_DECISION_TREE_RE = re.compile(r"^## (\d+\.\d+\..+)$", re.MULTILINE)
# SOP split threshold (plan: 300–800 tokens); rough estimate without tiktoken.
_MAX_SOP_TOKENS = 800
_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """
    Approximate token count without calling the tokenizer.
    """

    return max(1, len(text) // _CHARS_PER_TOKEN)


def _prefix(section: str, title: str, content_type: ContentType, body: str) -> str:
    """
    Retrieval prefix prepended to every chunk (Russian labels match source document).
    """
    
    return f"[Раздел: {section} > {title}]\n[Тип: {content_type.value}]\n{body.strip()}"


def _extract_faq_chunks(text: str, node: DocumentNode, source_path: str) -> list[ChunkDraft]:
    """
    One question/answer pair = one atomic chunk.
    """
    
    chunks: list[ChunkDraft] = []

    for match in _FAQ_PAIR_RE.finditer(text):
        question = match.group("question").strip()
        answer = match.group("answer").strip()
        body = f"**Вопрос:** {question}\n**Ответ:** {answer}"
        content = _prefix(node.section, question[:80], ContentType.FAQ, body)
        chunks.append(
            ChunkDraft(
                content=content,
                content_type=ContentType.FAQ,
                section=node.section,
                title=question[:120],
                node_id=f"{node.id}.faq.{len(chunks)}",
                token_count=estimate_tokens(content),
                source_path=source_path,
            )
        )

    return chunks


def _extract_glossary_chunks(text: str, node: DocumentNode, source_path: str) -> list[ChunkDraft]:
    """
    One line **Term:** definition = one chunk.
    """
    
    chunks: list[ChunkDraft] = []

    for match in _GLOSSARY_TERM_RE.finditer(text):
        term = match.group("term").strip()
        definition = match.group("definition").strip()
        body = f"**{term}:** {definition}"
        content = _prefix(node.section, term, ContentType.GLOSSARY, body)
        chunks.append(
            ChunkDraft(
                content=content,
                content_type=ContentType.GLOSSARY,
                section=node.section,
                title=term,
                node_id=f"{node.id}.term.{len(chunks)}",
                token_count=estimate_tokens(content),
                source_path=source_path,
            )
        )

    return chunks


def _split_sop_node(node: DocumentNode, source_path: str) -> list[ChunkDraft]:
    """
    SOP chunk = entire ## section; if over token limit, split by ###
    with parent H2 title as context prefix.
    """
    
    body = node.text.strip()
    if not body:
        return []

    full_content = _prefix(node.section, node.title, ContentType.SOP, body)
    if estimate_tokens(full_content) <= _MAX_SOP_TOKENS or node.level != 2:
        return [
            ChunkDraft(
                content=full_content,
                content_type=ContentType.SOP,
                section=node.section,
                title=node.title,
                node_id=node.id,
                token_count=estimate_tokens(full_content),
                source_path=source_path,
            )
        ]

    chunks: list[ChunkDraft] = []
    h3_pattern = re.compile(r"^### (.+)$", re.MULTILINE)
    matches = list(h3_pattern.finditer(body))

    if not matches:
        # Long section with no ### — keep as one chunk rather than drop text.
        return [
            ChunkDraft(
                content=full_content,
                content_type=ContentType.SOP,
                section=node.section,
                title=node.title,
                node_id=node.id,
                token_count=estimate_tokens(full_content),
                source_path=source_path,
            )
        ]

    parent_index: int | None = None
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        h3_title = match.group(1).strip()
        h3_body = body[start:end].strip()
        context = f"Контекст: {node.title}\n\n{h3_body}"
        content = _prefix(node.section, f"{node.title} > {h3_title}", ContentType.SOP, context)
        chunk = ChunkDraft(
            content=content,
            content_type=ContentType.SOP,
            section=node.section,
            title=h3_title,
            node_id=f"{node.id}.part.{index}",
            parent_chunk_index=parent_index,
            token_count=estimate_tokens(content),
            source_path=source_path,
        )
        
        # parent_chunk_index maps to chunk_meta.parent_id (parts of the same H2).
        if parent_index is None:
            parent_index = len(chunks)
        
        chunks.append(chunk)

    return chunks


def _split_by_pattern(
    text: str,
    pattern: re.Pattern[str],
    node: DocumentNode,
    content_type: ContentType,
    source_path: str,
) -> list[ChunkDraft]:
    """
    Split by ## heading regex (scenarios, decision trees).
    Each match starts a new chunk; trees and scenarios are never split mid-body.
    """
    
    matches = list(pattern.finditer(text))
    if not matches:
        content = _prefix(node.section, node.title, content_type, text)
        return [
            ChunkDraft(
                content=content,
                content_type=content_type,
                section=node.section,
                title=node.title,
                node_id=node.id,
                token_count=estimate_tokens(content),
                source_path=source_path,
            )
        ]

    chunks: list[ChunkDraft] = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        content = _prefix(node.section, title, content_type, body)
        chunks.append(
            ChunkDraft(
                content=content,
                content_type=content_type,
                section=node.section,
                title=title,
                node_id=f"{node.id}.{index}",
                token_count=estimate_tokens(content),
                source_path=source_path,
            )
        )

    return chunks


def chunk_node(node: DocumentNode, source_path: str) -> list[ChunkDraft]:
    """
    Convert a single document node into one or more chunks.
    """

    text = node.text.strip()
    if not text and node.content_type not in {ContentType.META, ContentType.OUT_OF_SCOPE}:
        return []

    if node.content_type == ContentType.FAQ:
        faq_chunks = _extract_faq_chunks(text, node, source_path)
        # Fallback when regex finds no pairs — one chunk for the whole FAQ section.
        return faq_chunks or [
            ChunkDraft(
                content=_prefix(node.section, node.title, ContentType.FAQ, text),
                content_type=ContentType.FAQ,
                section=node.section,
                title=node.title,
                node_id=node.id,
                token_count=estimate_tokens(text),
                source_path=source_path,
            )
        ]

    if node.content_type == ContentType.GLOSSARY:
        glossary_chunks = _extract_glossary_chunks(text, node, source_path)
        return glossary_chunks or [
            ChunkDraft(
                content=_prefix(node.section, node.title, ContentType.GLOSSARY, text),
                content_type=ContentType.GLOSSARY,
                section=node.section,
                title=node.title,
                node_id=node.id,
                token_count=estimate_tokens(text),
                source_path=source_path,
            )
        ]

    if node.content_type == ContentType.DECISION_TREE:
        return _split_by_pattern(text, _DECISION_TREE_RE, node, ContentType.DECISION_TREE, source_path)

    if node.content_type == ContentType.SCENARIO:
        return _split_by_pattern(text, _SCENARIO_RE, node, ContentType.SCENARIO, source_path)

    if node.content_type in {ContentType.META, ContentType.OUT_OF_SCOPE}:
        # Separate chunks per ## help the router (sections 00 and 13).
        h2_parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
        if len(h2_parts) > 1:
            chunks: list[ChunkDraft] = []
            # re.split alternates: [before first ##, title1, body1, title2, body2, ...]
            for index in range(1, len(h2_parts), 2):
                title = h2_parts[index].strip()
                body = h2_parts[index + 1].strip() if index + 1 < len(h2_parts) else ""
                if not body:
                    continue
                content = _prefix(node.section, title, node.content_type, body)
                chunks.append(
                    ChunkDraft(
                        content=content,
                        content_type=node.content_type,
                        section=node.section,
                        title=title,
                        node_id=f"{node.id}.{index // 2}",
                        token_count=estimate_tokens(content),
                        source_path=source_path,
                    )
                )
            if chunks:
                return chunks

        content = _prefix(node.section, node.title, node.content_type, text)
        return [
            ChunkDraft(
                content=content,
                content_type=node.content_type,
                section=node.section,
                title=node.title,
                node_id=node.id,
                token_count=estimate_tokens(content),
                source_path=source_path,
            )
        ]

    if node.content_type == ContentType.SOP and node.level == 2:
        return _split_sop_node(node, source_path)

    if node.content_type == ContentType.SOP and node.level == 3:
        # Already handled when splitting parent H2 in _split_sop_node.
        return []

    # SOP level=1 with no ## subsections inside the H1 block.
    content = _prefix(node.section, node.title, ContentType.SOP, text)
    return [
        ChunkDraft(
            content=content,
            content_type=ContentType.SOP,
            section=node.section,
            title=node.title,
            node_id=node.id,
            token_count=estimate_tokens(content),
            source_path=source_path,
        )
    ]


def chunk_document(text: str, source_path: str = "") -> list[ChunkDraft]:
    """
    Parse markdown and produce retrieval chunks.
    """

    nodes = parse_markdown(text, source_path=source_path)
    chunks: list[ChunkDraft] = []

    for node in nodes:
        chunks.extend(chunk_node(node, source_path))

    for chunk in chunks:
        chunk.content_hash = content_hash(chunk.content)

    return chunks
