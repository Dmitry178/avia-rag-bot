"""LLM-based reranking of retrieved chunks."""

from app.core.rag_constants import RERANK_TOP_N
from app.llm.chat import ChatCompletionClient
from app.rag.methods._llm_utils import parse_json_index_array
from app.rag.methods.base import RerankMethod
from app.rag.prompts import rerank_prompt
from app.rag.types import RetrievedChunk


class LlmRerankMethod(RerankMethod):
    """
    LLM-based reranking of retrieved chunk candidates.
    """

    name = "rerank"

    def __init__(self, llm: ChatCompletionClient) -> None:
        self._llm = llm

    async def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        *,
        top_n: int = RERANK_TOP_N,
    ) -> list[RetrievedChunk]:
        if len(candidates) <= top_n:
            return candidates

        preview = candidates[: min(len(candidates), 20)]
        documents = "\n\n".join(
            f"[{index}] {item.chunk.title}\n{item.chunk.content[:700]}"
            for index, item in enumerate(preview)
        )

        text, _metadata = await self._llm.complete(
            [{"role": "user", "content": rerank_prompt(query, documents, top_n=top_n)}],
            system_prompt="You rank documents by relevance. Return JSON only.",
            harden_user_messages=False,
        )

        ordered_indices = parse_json_index_array(text)
        reranked: list[RetrievedChunk] = []
        seen: set[int] = set()

        for index in ordered_indices:
            if index < 0 or index >= len(preview) or index in seen:
                continue
            seen.add(index)
            reranked.append(preview[index])
            if len(reranked) >= top_n:
                break

        if reranked:
            return reranked

        return preview[:top_n]
