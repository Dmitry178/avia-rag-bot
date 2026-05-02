"""OpenAI-compatible LLM clients (chat completions and embeddings)."""

from app.llm.chat import ChatCompletionClient
from app.llm.embeddings import EmbeddingClient

__all__ = ["ChatCompletionClient", "EmbeddingClient"]
