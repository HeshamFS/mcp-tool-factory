"""Google (Gemini) provider implementation."""

import logging
from typing import Any

from tool_factory.providers.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GoogleProvider(BaseLLMProvider):
    """Provider for Google's Gemini models."""

    def _initialize_client(self) -> None:
        """Initialize the Google Generative AI client."""
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        self._client = genai.GenerativeModel(self.model)

    def _call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> LLMResponse:
        """Make API call to Google."""
        # Google combines system and user prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        response = self._client.generate_content(
            full_prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": self.temperature,
            },
        )

        text = response.text

        # Build raw response for logging
        raw_response = None
        try:
            raw_response = {
                "text": text,
                "candidates": str(response.candidates) if hasattr(response, 'candidates') else None,
                "prompt_feedback": str(response.prompt_feedback) if hasattr(response, 'prompt_feedback') else None,
            }
        except Exception as e:
            logger.debug(f"Failed to capture response object: {e}")

        return LLMResponse(
            text=text,
            tokens_in=None,  # Google doesn't expose token counts easily
            tokens_out=None,
            model=self.model,
            raw_response=raw_response,
        )
