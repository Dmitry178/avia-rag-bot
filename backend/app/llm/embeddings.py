"""OpenAI-compatible embedding client."""

import httpx

from collections.abc import AsyncIterator, Callable

from app.core.config import LLMSettings
from app.exceptions.service import ServiceError

EMBED_BATCH_SIZE = 32


class EmbeddingClient:
    """
    Batch embedding via {LLM__BASE_URL}/embeddings endpoint.
    """

    def __init__(self, settings: LLMSettings) -> None:
        self._settings = settings

    def _validate_config(self) -> None:
        if not self._settings.base_url:
            raise ServiceError(
                detail="LLM__BASE_URL is not configured",
                error_code="embedding_config_error",
                status_code=400,
            )

        if not self._settings.embedding_model:
            raise ServiceError(
                detail="LLM__EMBEDDING_MODEL is not configured",
                error_code="embedding_config_error",
                status_code=400,
            )

    async def _post_embedding_batch(
        self,
        client: httpx.AsyncClient,
        batch: list[str],
    ) -> list[list[float]]:
        """
        Request embeddings for a single batch.
        """

        headers = {"Authorization": f"Bearer {self._settings.api_key}"} if self._settings.api_key else {}
        base_url = self._settings.base_url.rstrip("/")
        response = await client.post(
            f"{base_url}/embeddings",
            headers=headers,
            json={"model": self._settings.embedding_model, "input": batch},
        )

        if response.status_code >= 400:
            raise ServiceError(
                detail=f"Embedding API error: {response.status_code}",
                error_code="embedding_api_error",
                status_code=502,
                extra={"body": response.text[:500]},
            )

        payload = response.json()
        data = sorted(payload["data"], key=lambda item: item["index"])

        return [item["embedding"] for item in data]

    async def iter_embed_batches(self, texts: list[str]) -> AsyncIterator[list[list[float]]]:
        """
        Yield embedding vectors batch by batch in input order.
        """

        self._validate_config()

        if not texts:
            return

        async with httpx.AsyncClient(timeout=120.0) as client:
            for offset in range(0, len(texts), EMBED_BATCH_SIZE):
                batch = texts[offset : offset + EMBED_BATCH_SIZE]
                yield await self._post_embedding_batch(client, batch)

    async def embed_texts(
        self,
        texts: list[str],
        *,
        on_batch_complete: Callable[[int, int], None] | None = None,
    ) -> list[list[float]]:
        """
        Embed texts in batches and return vectors in the same order.
        """

        vectors: list[list[float]] = []
        total = len(texts)

        async for batch_vectors in self.iter_embed_batches(texts):
            vectors.extend(batch_vectors)
            if on_batch_complete is not None:
                on_batch_complete(len(vectors), total)

        return vectors
