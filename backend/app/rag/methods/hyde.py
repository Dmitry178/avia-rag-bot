"""HyDE query transformation."""

from app.llm.chat import ChatCompletionClient
from app.rag.methods.base import QueryTransformMethod
from app.rag.prompts import hyde_prompt
from app.rag.types import RagQueryContext


class HyDEQueryMethod(QueryTransformMethod):
    """
    HyDE: generate a hypothetical answer passage and search by its embedding.
    """

    name = "hyde"

    def __init__(self, llm: ChatCompletionClient) -> None:
        self._llm = llm

    async def build_search_queries(self, ctx: RagQueryContext) -> list[str]:
        text, _metadata = await self._llm.complete(
            [{"role": "user", "content": hyde_prompt(ctx.query)}],
            system_prompt=(
                "You generate concise hypothetical knowledge-base passages for semantic search."
            ),
            harden_user_messages=False,
        )

        passage = text.strip()

        return [passage] if passage else [ctx.query]
