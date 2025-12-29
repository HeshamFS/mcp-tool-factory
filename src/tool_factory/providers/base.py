"""Base LLM Provider interface."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    """Structured response from an LLM provider."""

    text: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: float = 0.0
    model: str | None = None
    raw_response: dict[str, Any] | None = None
    error: str | None = None
    error_traceback: str | None = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    All provider implementations must inherit from this class and implement
    the required methods.
    """

    def __init__(self, api_key: str, model: str, **kwargs: Any) -> None:
        """Initialize the provider.

        Args:
            api_key: API key for the provider
            model: Model identifier to use
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.model = model
        self.temperature = kwargs.get("temperature", 0.7)
        self._client: Any = None

    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize the provider-specific client."""
        pass

    @abstractmethod
    def _call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> LLMResponse:
        """Make the actual API call to the provider.

        Args:
            system_prompt: System instructions for the model
            user_prompt: User's prompt/query
            max_tokens: Maximum tokens in the response

        Returns:
            LLMResponse with text and metadata
        """
        pass

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Call the LLM with timing and error handling.

        Args:
            system_prompt: System instructions for the model
            user_prompt: User's prompt/query
            max_tokens: Maximum tokens in the response

        Returns:
            LLMResponse with text and metadata
        """
        import traceback

        start_time = time.time()

        try:
            if self._client is None:
                self._initialize_client()

            response = self._call_api(system_prompt, user_prompt, max_tokens)
            response.latency_ms = (time.time() - start_time) * 1000
            return response

        except Exception as e:
            return LLMResponse(
                text="",
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e),
                error_traceback=traceback.format_exc(),
            )

    @property
    def provider_name(self) -> str:
        """Return the provider name for logging."""
        return self.__class__.__name__.replace("Provider", "")
