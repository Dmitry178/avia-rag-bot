"""Select active RAG methods from configuration."""

from app.llm.chat import ChatCompletionClient
from app.rag.methods.base import QueryTransformMethod, RerankMethod
from app.rag.methods.hyde import HyDEQueryMethod
from app.rag.methods.multi_query import MultiQueryMethod
from app.rag.methods.query_rewriting import QueryRewritingMethod
from app.rag.methods.rerank import LlmRerankMethod
from app.schemas.rag import RagConfig


def resolve_query_transform_method(
    rag_config: RagConfig,
    llm: ChatCompletionClient,
) -> QueryTransformMethod | None:
    """
    Return the active exclusive query method, if any.
    """

    if rag_config.use_hyde:
        return HyDEQueryMethod(llm)

    if rag_config.use_multi_query:
        return MultiQueryMethod(llm)

    if rag_config.use_query_rewriting:
        return QueryRewritingMethod(llm)

    return None


def resolve_rerank_method(
    rag_config: RagConfig,
    llm: ChatCompletionClient,
) -> RerankMethod | None:
    """
    Return reranker when enabled in config.
    """

    if rag_config.use_rerank:
        return LlmRerankMethod(llm)

    return None
