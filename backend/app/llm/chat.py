"""OpenAI-compatible chat completions client."""

import httpx
import time

from typing import Any

from app.core.config import LLMSettings
from app.exceptions.service import ServiceError
from app.llm.prompt_guard import harden_messages_for_llm
from app.llm.prompts import SYSTEM_PROMPT


class ChatCompletionClient:
    """
    Synchronous (non-streaming) chat via {LLM__BASE_URL}/chat/completions.
    """

    def __init__(self, settings: LLMSettings) -> None:
        self._settings = settings

    def _validate_config(self) -> None:
        if not self._settings.base_url:
            raise ServiceError(
                detail="LLM__BASE_URL is not configured",
                error_code="llm_config_error",
                status_code=400,
            )
        if not self._settings.model:
            raise ServiceError(
                detail="LLM__MODEL is not configured",
                error_code="llm_config_error",
                status_code=400,
            )

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Run a chat completion and return (assistant_text, metadata dict).
        """

        self._validate_config()

        resolved_system_prompt = system_prompt or SYSTEM_PROMPT
        payload_messages = [{"role": "system", "content": resolved_system_prompt}]
        payload_messages.extend(harden_messages_for_llm(messages))

        headers: dict[str, str] = {}
        if self._settings.api_key:
            headers["Authorization"] = f"Bearer {self._settings.api_key}"

        base_url = self._settings.base_url.rstrip("/")
        started = time.perf_counter()

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self._settings.model,
                    "messages": payload_messages,
                    "stream": False,
                },
            )

        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code >= 400:
            raise ServiceError(
                detail=f"Chat completion API error: {response.status_code}",
                error_code="llm_api_error",
                status_code=502,
                extra={"body": response.text[:500]},
            )

        body = response.json()
        choice = body["choices"][0]["message"]["content"]
        usage = body.get("usage") or {}

        metadata = {
            "model": body.get("model") or self._settings.model,
            "latency_ms": latency_ms,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }

        return str(choice), metadata
