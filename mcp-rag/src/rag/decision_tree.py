"""Dedicated lane verification prompts (domain-specific handlers)."""

import re

from dataclasses import dataclass
from typing import Any

from src.core.rag_constants import DECISION_TREE_NO_MATCH_TOKEN
from src.llm.chat import ChatCompletionClient
from src.rag.retrieval_lanes import LanePresentation, RetrievalLane
from src.rag.types import RetrievedChunk, chunk_similarity

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


def _normalize_no_match_line(line: str) -> str:
    """
    Strip wrappers and punctuation from one response line.
    """

    stripped = line.strip()
    without_wrappers = re.sub(r"^[`\"'*_\s]+|[`\"'*_\s.:;,!?]+$", "", stripped)

    return without_wrappers.upper()


def is_verification_no_match(response: str, *, no_match_token: str) -> bool:
    """
    Return True when the model signals that the candidate does not answer the question.
    """

    if not response.strip():
        return True

    token = no_match_token.upper()

    return any(_normalize_no_match_line(line) == token for line in response.splitlines())


def is_decision_tree_no_match(response: str) -> bool:
    """
    Return True when the model signals that the tree does not answer the question.
    """

    return is_verification_no_match(response, no_match_token=DECISION_TREE_NO_MATCH_TOKEN)


def build_decision_tree_system_prompt(
    *,
    tree: RetrievedChunk,
    reply_language: str | None,
    no_match_token: str = DECISION_TREE_NO_MATCH_TOKEN,
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
        f"Reply with exactly this token and nothing else: {no_match_token}\n\n"
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
    no_match_token: str = DECISION_TREE_NO_MATCH_TOKEN,
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
        no_match_token=no_match_token,
    )

    guidance_text, _metadata = await llm.complete(
        [{"role": "user", "content": query}],
        system_prompt=system_prompt,
        harden_user_messages=False,
    )

    if is_verification_no_match(guidance_text, no_match_token=no_match_token):
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


async def generate_lane_verification_guidance(
    llm: ChatCompletionClient,
    *,
    query: str,
    hit: RetrievedChunk,
    lane: RetrievalLane,
    reply_language: str | None,
) -> DecisionTreeGuidance | None:
    """
    Dispatch dedicated LLM verification for a schema-configured lane presentation.
    """

    presentation = lane.presentation
    if presentation.verification_strategy != "dedicated_llm":
        return None

    if presentation.ui_variant == "decision_tree":
        token = presentation.verification_no_match_token or DECISION_TREE_NO_MATCH_TOKEN
        return await generate_decision_tree_guidance(
            llm,
            query=query,
            tree=hit,
            reply_language=reply_language,
            no_match_token=token,
        )

    return None


def verification_metadata_key(presentation: LanePresentation) -> str | None:
    """
    Return assistant metadata key for a verified lane presentation.
    """

    if presentation.ui_variant == "decision_tree":
        return "decision_tree_guidance"

    return None
