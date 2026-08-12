"""Multi-Query retrieval expansion."""

from src.core.rag_constants import MULTI_QUERY_COUNT
from src.llm.chat import ChatCompletionClient
from src.rag.methods._llm_utils import parse_json_string_array
from src.rag.methods.base import QueryTransformMethod
from src.rag.prompts import multi_query_prompt
from src.rag.types import RagQueryContext


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
