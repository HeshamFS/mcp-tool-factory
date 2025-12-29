"""OpenAI provider implementation."""

import logging
from typing import Any

from tool_factory.providers.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """Provider for OpenAI's GPT models."""

    def _initialize_client(self) -> None:
        """Initialize the OpenAI client."""
        import openai

        self._client = openai.OpenAI(api_key=self.api_key)

    def _call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> LLMResponse:
        """Make API call to OpenAI."""
        # Handle newer models that use max_completion_tokens
        is_new_model = self.model.startswith(("gpt-5", "gpt-4.1", "o3", "o4"))
        token_param = "max_completion_tokens" if is_new_model else "max_tokens"

        response = self._client.chat.completions.create(
            model=self.model,
            **{token_param: max_tokens},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        text = response.choices[0].message.content
        tokens_in = None
        tokens_out = None

        if hasattr(response, 'usage'):
            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens

        # Build raw response for logging
        raw_response = None
        try:
            raw_response = {
                "id": response.id if hasattr(response, 'id') else None,
                "model": response.model if hasattr(response, 'model') else None,
                "created": response.created if hasattr(response, 'created') else None,
                "usage": {
                    "prompt_tokens": tokens_in,
                    "completion_tokens": tokens_out,
                    "total_tokens": (tokens_in or 0) + (tokens_out or 0),
                },
                "choices": [{
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": response.choices[0].finish_reason if response.choices else None,
                }],
            }
        except Exception as e:
            logger.debug(f"Failed to capture response object: {e}")

        return LLMResponse(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=self.model,
            raw_response=raw_response,
        )
