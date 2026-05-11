"""RAG pipeline configuration schemas."""

from pydantic import BaseModel, Field


class RagConfig(BaseModel):
    """
    Toggle flags for optional RAG retrieval stages.
    """

    use_hyde: bool | None = Field(
        default=None,
        description="Enable HyDE (hypothetical document embeddings) retrieval.",
    )
    use_multi_query: bool | None = Field(
        default=None,
        description="Enable multi-query retrieval with result fusion.",
    )
    use_query_rewriting: bool | None = Field(
        default=None,
        description="Enable query rewriting before retrieval.",
    )
    use_rerank: bool | None = Field(
        default=None,
        description="Enable cross-encoder reranking after vector search.",
    )

    def to_metadata_dict(self) -> dict[str, bool]:
        """
        Return a compact dict with only non-null flags for message metadata.
        """

        payload: dict[str, bool] = {}

        if self.use_hyde is not None:
            payload["use_hyde"] = self.use_hyde

        if self.use_multi_query is not None:
            payload["use_multi_query"] = self.use_multi_query

        if self.use_query_rewriting is not None:
            payload["use_query_rewriting"] = self.use_query_rewriting

        if self.use_rerank is not None:
            payload["use_rerank"] = self.use_rerank

        return payload
