"""Anthropic (Claude) provider implementation."""

import logging
from typing import Any

from tool_factory.providers.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Provider for Anthropic's Claude models."""

    def _initialize_client(self) -> None:
        """Initialize the Anthropic client."""
        import anthropic

        self._client = anthropic.Anthropic(api_key=self.api_key)

    def _call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> LLMResponse:
        """Make API call to Anthropic."""
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = response.content[0].text
        tokens_in = response.usage.input_tokens if hasattr(response, 'usage') else None
        tokens_out = response.usage.output_tokens if hasattr(response, 'usage') else None

        # Build raw response for logging
        raw_response = None
        try:
            raw_response = {
                "id": response.id if hasattr(response, 'id') else None,
                "type": response.type if hasattr(response, 'type') else None,
                "role": response.role if hasattr(response, 'role') else None,
                "model": response.model if hasattr(response, 'model') else None,
                "stop_reason": response.stop_reason if hasattr(response, 'stop_reason') else None,
                "usage": {
                    "input_tokens": tokens_in,
                    "output_tokens": tokens_out,
                },
                "content": [{"type": "text", "text": text}],
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
