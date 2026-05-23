"""Multi-Query retrieval expansion."""

from app.core.rag_constants import MULTI_QUERY_COUNT
from app.llm.chat import ChatCompletionClient
from app.rag.methods._llm_utils import parse_json_string_array
from app.rag.methods.base import QueryTransformMethod
from app.rag.prompts import multi_query_prompt
from app.rag.types import RagQueryContext


class MultiQueryMethod(QueryTransformMethod):
    """
    Multi-Query: generate several query variants for fusion retrieval.
    """

    name = "multi_query"

    def __init__(self, llm: ChatCompletionClient) -> None:
        self._llm = llm

    async def build_search_queries(self, ctx: RagQueryContext) -> list[str]:
        text, _metadata = await self._llm.complete(
            [{"role": "user", "content": multi_query_prompt(ctx.query)}],
            system_prompt="You generate search queries for airport knowledge retrieval. Return JSON only.",
            harden_user_messages=False,
        )

        variants = parse_json_string_array(text)
        unique = list(dict.fromkeys(variants))

        if not unique:
            return [ctx.query]

        return unique[:MULTI_QUERY_COUNT]
