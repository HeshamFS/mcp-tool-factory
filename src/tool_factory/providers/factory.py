"""Provider factory for creating LLM providers."""

from typing import Any

from tool_factory.config import LLMProvider as LLMProviderEnum
from tool_factory.providers.anthropic import AnthropicProvider
from tool_factory.providers.base import BaseLLMProvider
from tool_factory.providers.claude_code import ClaudeCodeProvider
from tool_factory.providers.google import GoogleProvider
from tool_factory.providers.openai import OpenAIProvider


def create_provider(
    provider: LLMProviderEnum | str,
    api_key: str,
    model: str,
    **kwargs: Any,
) -> BaseLLMProvider:
    """Create an LLM provider instance based on the provider type.

    Args:
        provider: The provider type (enum or string)
        api_key: API key for the provider
        model: Model identifier
        **kwargs: Additional provider-specific configuration

    Returns:
        Configured provider instance

    Raises:
        ValueError: If provider type is not supported
    """
    # Convert string to enum if needed
    if isinstance(provider, str):
        provider = LLMProviderEnum(provider)

    provider_map = {
        LLMProviderEnum.ANTHROPIC: AnthropicProvider,
        LLMProviderEnum.OPENAI: OpenAIProvider,
        LLMProviderEnum.GOOGLE: GoogleProvider,
        LLMProviderEnum.CLAUDE_CODE: ClaudeCodeProvider,
    }

    provider_class = provider_map.get(provider)
    if provider_class is None:
        raise ValueError(f"Unsupported provider: {provider}")

    return provider_class(api_key=api_key, model=model, **kwargs)
