"""LLM chat configuration schemas."""

from pydantic import BaseModel, Field


class LlmConfig(BaseModel):
    """
    Toggle flags and text for plain LLM chat mode.
    """

    use_custom_prompt: bool | None = Field(
        default=None,
        description="When true, use custom_prompt as system prompt and disable guards.",
    )
    custom_prompt: str | None = Field(
        default=None,
        description="Custom system prompt text; ignored when use_custom_prompt is false.",
    )
