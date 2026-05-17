"""RAG method base classes."""

from abc import ABC, abstractmethod

from app.rag.types import RagQueryContext, RetrievedChunk


class QueryTransformMethod(ABC):
    """
    Produces one or more search queries from the user question.
    """

    name: str

    @abstractmethod
    async def build_search_queries(self, ctx: RagQueryContext) -> list[str]:
        """
        Return search strings to embed and retrieve against FAISS.
        """


class RerankMethod(ABC):
    """
    Re-orders retrieved chunks before context assembly.
    """

    name: str

    @abstractmethod
    async def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        *,
        top_n: int,
    ) -> list[RetrievedChunk]:
        """
        Return the top_n most relevant chunks.
        """
