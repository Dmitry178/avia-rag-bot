"""Turn parsed document nodes into retrieval chunks."""

import re

from etl.hashing import content_hash
from etl.parser import parse_markdown
from etl.profile import DocumentProfile
from etl.types import ChunkDraft, ContentType, DocumentNode


def estimate_tokens(text: str, profile: DocumentProfile) -> int:
    """
    Approximate token count without calling the tokenizer.
    """

    return max(1, len(text) // profile.chars_per_token)


def _prefix(
    profile: DocumentProfile,
    section: str,
    title: str,
    content_type: ContentType,
    body: str,
) -> str:
    """
    Retrieval prefix prepended to every chunk.
    """

    section_label = profile.labels.section
    type_label = profile.labels.type

    return (
        f"[{section_label}: {section} > {title}]\n"
        f"[{type_label}: {content_type.value}]\n"
        f"{body.strip()}"
    )


def _faq_prefix(profile: DocumentProfile, source_section: str, body: str) -> str:
    """
    FAQ retrieval prefix with explicit source chapter metadata.
    """

    section_label = profile.labels.section
    source_label = profile.labels.source
    type_label = profile.labels.type

    return (
        f"[{section_label}: {source_section} > FAQ]\n"
        f"[{source_label}: {source_section}]\n"
        f"[{type_label}: faq]\n"
        f"{body.strip()}"
    )


def _split_sop_and_faq(profile: DocumentProfile, body: str) -> tuple[str, str | None]:
    """
    Separate trailing per-chapter FAQ block from SOP body text.
    """

    match = profile.embedded_faq_block_re.search(body)
    if not match:
        return body.strip(), None

    sop_body = body[: match.start()].strip()
    faq_body = body[match.end() :].strip()

    return sop_body, faq_body or None


def _extract_faq_chunks(
    profile: DocumentProfile,
    text: str,
    node: DocumentNode,
    source_path: str,
    *,
    source_section: str | None = None,
) -> list[ChunkDraft]:
    """
    One question/answer pair = one atomic chunk.
    """

    origin = source_section or node.section
    chunks: list[ChunkDraft] = []
    question_marker = profile.faq_question_marker
    answer_marker = profile.faq_answer_marker

    for match in profile.faq_pair_re.finditer(text):
        question = match.group("question").strip()
        answer = match.group("answer").strip()
        body = f"{question_marker} {question}\n{answer_marker} {answer}"
        content = _faq_prefix(profile, origin, body)
        chunks.append(
            ChunkDraft(
                content=content,
                content_type=ContentType.FAQ,
                section=origin,
                title=question[:120],
                node_id=f"{node.id}.faq.{len(chunks)}",
                token_count=estimate_tokens(content, profile),
                source_path=source_path,
            )
        )

    return chunks


def _split_by_pattern(
    profile: DocumentProfile,
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
        content = _prefix(profile, node.section, node.title, content_type, text)
        return [
            ChunkDraft(
                content=content,
                content_type=content_type,
                section=node.section,
                title=node.title,
                node_id=node.id,
                token_count=estimate_tokens(content, profile),
                source_path=source_path,
            )
        ]

    chunks: list[ChunkDraft] = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        content = _prefix(profile, node.section, title, content_type, body)
        chunks.append(
            ChunkDraft(
                content=content,
                content_type=content_type,
                section=node.section,
                title=title,
                node_id=f"{node.id}.{index}",
                token_count=estimate_tokens(content, profile),
                source_path=source_path,
            )
        )

    return chunks


def _split_sop_body(
    *,
    profile: DocumentProfile,
    body: str,
    node: DocumentNode,
    source_path: str,
) -> list[ChunkDraft]:
    """
    Build SOP chunk(s) from H2 body text without the trailing FAQ block.
    """

    if not body:
        return []

    full_content = _prefix(profile, node.section, node.title, ContentType.SOP, body)

    if estimate_tokens(full_content, profile) <= profile.max_sop_tokens or node.level != 2:
        return [
            ChunkDraft(
                content=full_content,
                content_type=ContentType.SOP,
                section=node.section,
                title=node.title,
                node_id=node.id,
                token_count=estimate_tokens(full_content, profile),
                source_path=source_path,
            )
        ]

    chunks: list[ChunkDraft] = []
    h3_pattern = re.compile(r"^### (.+)$", re.MULTILINE)
    matches = list(h3_pattern.finditer(body))

    if not matches:
        return [
            ChunkDraft(
                content=full_content,
                content_type=ContentType.SOP,
                section=node.section,
                title=node.title,
                node_id=node.id,
                token_count=estimate_tokens(full_content, profile),
                source_path=source_path,
            )
        ]

    parent_index: int | None = None
    context_label = profile.labels.context

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        h3_title = match.group(1).strip()
        h3_body = body[start:end].strip()
        context = f"{context_label}: {node.title}\n\n{h3_body}"
        content = _prefix(profile, node.section, f"{node.title} > {h3_title}", ContentType.SOP, context)
        chunk = ChunkDraft(
            content=content,
            content_type=ContentType.SOP,
            section=node.section,
            title=h3_title,
            node_id=f"{node.id}.part.{index}",
            parent_chunk_index=parent_index,
            token_count=estimate_tokens(content, profile),
            source_path=source_path,
        )

        if parent_index is None:
            parent_index = len(chunks)

        chunks.append(chunk)

    return chunks


def _split_sop_node(profile: DocumentProfile, node: DocumentNode, source_path: str) -> list[ChunkDraft]:
    """
    SOP chunk = entire ## section (FAQ stripped); if over token limit, split by ###
    with parent H2 title as context prefix. FAQ pairs become separate faq chunks.
    """

    sop_body, faq_text = _split_sop_and_faq(profile, node.text.strip())
    chunks = _split_sop_body(profile=profile, body=sop_body, node=node, source_path=source_path)

    if faq_text:
        chunks.extend(
            _extract_faq_chunks(profile, faq_text, node, source_path, source_section=node.section),
        )

    return chunks


def chunk_node(profile: DocumentProfile, node: DocumentNode, source_path: str) -> list[ChunkDraft]:
    """
    Convert a single document node into one or more chunks.
    """

    if node.content_type in profile.skip_index_types:
        return []

    text = node.text.strip()
    if not text:
        return []

    if node.content_type == ContentType.FAQ:
        faq_chunks = _extract_faq_chunks(profile, text, node, source_path)
        return faq_chunks or [
            ChunkDraft(
                content=_faq_prefix(profile, node.section, text),
                content_type=ContentType.FAQ,
                section=node.section,
                title=node.title,
                node_id=node.id,
                token_count=estimate_tokens(text, profile),
                source_path=source_path,
            )
        ]

    if node.content_type == ContentType.DECISION_TREE:
        return _split_by_pattern(
            profile,
            text,
            profile.decision_tree_split_re,
            node,
            ContentType.DECISION_TREE,
            source_path,
        )

    if node.content_type == ContentType.SCENARIO:
        return _split_by_pattern(
            profile,
            text,
            profile.scenario_split_re,
            node,
            ContentType.SCENARIO,
            source_path,
        )

    if node.content_type == ContentType.SOP and node.level == 2:
        return _split_sop_node(profile, node, source_path)

    if node.content_type == ContentType.SOP and node.level == 3:
        # Already handled when splitting parent H2 in _split_sop_node.
        return []

    # SOP level=1 with no ## subsections inside the H1 block.
    sop_body, faq_text = _split_sop_and_faq(profile, text)
    chunks: list[ChunkDraft] = []

    if sop_body:
        sop_content = _prefix(profile, node.section, node.title, ContentType.SOP, sop_body)
        chunks.append(
            ChunkDraft(
                content=sop_content,
                content_type=ContentType.SOP,
                section=node.section,
                title=node.title,
                node_id=node.id,
                token_count=estimate_tokens(sop_content, profile),
                source_path=source_path,
            )
        )

    if faq_text:
        chunks.extend(
            _extract_faq_chunks(profile, faq_text, node, source_path, source_section=node.section),
        )

    return chunks


def chunk_document(
    text: str,
    profile: DocumentProfile,
    source_path: str = "",
) -> list[ChunkDraft]:
    """
    Parse markdown and produce retrieval chunks.
    """

    nodes = parse_markdown(text, profile=profile, source_path=source_path)
    chunks: list[ChunkDraft] = []

    for node in nodes:
        if node.content_type in profile.skip_index_types:
            continue
        chunks.extend(chunk_node(profile, node, source_path))

    for chunk in chunks:
        chunk.content_hash = content_hash(chunk.content)

    return chunks
