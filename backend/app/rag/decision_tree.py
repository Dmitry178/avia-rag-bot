"""Decision-tree detection and dedicated operational guidance generation."""

from dataclasses import dataclass
from typing import Any

from app.core.rag_constants import (
    DECISION_TREE_MAX_APPLICABLE,
    DECISION_TREE_MIN_SIMILARITY,
    DECISION_TREE_NO_MATCH_TOKEN,
)
from app.llm.chat import ChatCompletionClient
from app.rag.types import RetrievedChunk
from etl.types import ContentType

_DECISION_TREE_LANE = "decision_tree"

_REPLY_LANGUAGE_HINTS: dict[str, str] = {
    "ru": "The user's latest message is in Russian. Reply entirely in Russian; do not use English.",
    "en": "The user's latest message is in English. Reply entirely in English.",
}


@dataclass
class DecisionTreeGuidance:
    """
    Operational walkthrough produced from a matched decision-tree chunk.
    """

    chunk_id: int
    title: str
    section: str
    node_id: str
    similarity: float
    guidance: str

    def to_metadata(self) -> dict[str, Any]:
        """
        Serialize for assistant message metadata and UI rendering.
        """

        return {
            "chunk_id": self.chunk_id,
            "title": self.title,
            "section": self.section,
            "node_id": self.node_id,
            "similarity": round(self.similarity, 4),
            "guidance": self.guidance,
        }


def chunk_similarity(item: RetrievedChunk) -> float:
    """
    Return the best available similarity score for a retrieved chunk.
    """

    if item.vector_similarity is not None:
        return item.vector_similarity

    return item.score


def select_applicable_decision_trees(
    lane_results: dict[str, list[RetrievedChunk]],
    *,
    min_similarity: float = DECISION_TREE_MIN_SIMILARITY,
    max_trees: int = DECISION_TREE_MAX_APPLICABLE,
) -> list[RetrievedChunk]:
    """
    Pick decision-tree lane hits that are similar enough to verify with the LLM.

    Vector similarity is only a pre-filter; the dedicated prompt must confirm
    that the tree substantively answers the user's situation.
    """

    hits = lane_results.get(_DECISION_TREE_LANE, [])
    applicable = [hit for hit in hits if chunk_similarity(hit) >= min_similarity]

    return applicable[:max_trees]


def exclude_decision_tree_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """
    Remove decision-tree chunks from the general RAG context list.
    """

    return [item for item in chunks if item.chunk.content_type != ContentType.DECISION_TREE.value]


def is_decision_tree_no_match(response: str) -> bool:
    """
    Return True when the model signals that the tree does not answer the question.
    """

    normalized = response.strip()
    if not normalized:
        return True

    token = DECISION_TREE_NO_MATCH_TOKEN.upper()
    if normalized.upper() == token:
        return True

    first_line = normalized.splitlines()[0].strip().upper()
    return first_line == token


def build_decision_tree_system_prompt(
    *,
    tree: RetrievedChunk,
    reply_language: str | None,
) -> str:
    """
    Build the dedicated system prompt for decision-tree walkthrough.

    Does not reuse the general aviation chat prompt — only tree-fit logic applies.
    """

    chunk = tree.chunk
    language_hint = (
        _REPLY_LANGUAGE_HINTS[reply_language]
        if reply_language is not None and reply_language in _REPLY_LANGUAGE_HINTS
        else ""
    )
    language_block = f"\n{language_hint}" if language_hint else ""

    return (
        "You are an operational assistant for airport staff. "
        "You receive ONE decision tree from the knowledge base and the user's question.\n\n"
        "Task:\n"
        "1. Decide whether this decision tree **substantively answers** the user's operational "
        "situation — not merely a loose keyword overlap.\n"
        "2. If YES — walk through the matching branch and output a numbered operational checklist. "
        "Start with immediate actions. Use only steps present in the tree. "
        "For branching trees, pick the branch that best fits the situation; "
        "if ambiguous, state your assumption in one short phrase.\n"
        f"3. If NO — the tree topic or branches do not fit the question. "
        f"Reply with exactly this token and nothing else: {DECISION_TREE_NO_MATCH_TOKEN}\n\n"
        "Examples of NO match: cargo spill on the runway vs a tree about suspicious items; "
        "fire alarm vs a tree about passenger complaints.\n"
        "Do not output refusal messages, definitions, or background when the tree does not fit."
        f"{language_block}\n\n"
        f"Decision tree ({chunk.section} / {chunk.title}):\n"
        f"{chunk.content}"
    )


async def generate_decision_tree_guidance(
    llm: ChatCompletionClient,
    *,
    query: str,
    tree: RetrievedChunk,
    reply_language: str | None,
) -> DecisionTreeGuidance | None:
    """
    Run a dedicated LLM call to walk through the matched decision tree.

    Returns None when the model replies with the no-match token.
    """

    chunk = tree.chunk
    if chunk.id is None:
        return None

    system_prompt = build_decision_tree_system_prompt(
        tree=tree,
        reply_language=reply_language,
    )

    guidance_text, _metadata = await llm.complete(
        [{"role": "user", "content": query}],
        system_prompt=system_prompt,
        harden_user_messages=False,
    )

    if is_decision_tree_no_match(guidance_text):
        return None

    guidance = guidance_text.strip()
    if not guidance:
        return None

    return DecisionTreeGuidance(
        chunk_id=chunk.id,
        title=chunk.title,
        section=chunk.section,
        node_id=chunk.node_id,
        similarity=chunk_similarity(tree),
        guidance=guidance,
    )
