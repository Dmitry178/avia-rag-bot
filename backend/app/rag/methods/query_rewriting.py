"""Query rewriting using conversation context."""

from app.llm.chat import ChatCompletionClient
from app.rag.methods._llm_utils import format_history
from app.rag.methods.base import QueryTransformMethod
from app.rag.prompts import query_rewriting_prompt
from app.rag.types import RagQueryContext


class QueryRewritingMethod(QueryTransformMethod):
    """
    Query Rewriting: rewrite the user question using dialog context.
    """

    name = "query_rewriting"

    def __init__(self, llm: ChatCompletionClient) -> None:
        self._llm = llm

    async def build_search_queries(self, ctx: RagQueryContext) -> list[str]:
        text, _metadata = await self._llm.complete(
            [
                {
                    "role": "user",
                    "content": query_rewriting_prompt(ctx.query, format_history(ctx.history)),
                }
            ],
            system_prompt="You rewrite user questions into standalone search queries.",
            harden_user_messages=False,
        )

        rewritten = text.strip()

        return [rewritten] if rewritten else [ctx.query]
