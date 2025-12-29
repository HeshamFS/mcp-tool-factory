"""Tests for LLM provider implementations."""

import pytest
from unittest.mock import MagicMock, patch

from tool_factory.providers.base import BaseLLMProvider, LLMResponse
from tool_factory.providers.factory import create_provider
from tool_factory.config import LLMProvider as LLMProviderEnum


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_basic_response(self):
        """Test creating a basic response."""
        response = LLMResponse(text="Hello, world!")
        assert response.text == "Hello, world!"
        assert response.tokens_in is None
        assert response.error is None

    def test_full_response(self):
        """Test creating a response with all fields."""
        response = LLMResponse(
            text="Hello",
            tokens_in=10,
            tokens_out=5,
            latency_ms=100.0,
            model="test-model",
            raw_response={"id": "123"},
        )
        assert response.text == "Hello"
        assert response.tokens_in == 10
        assert response.tokens_out == 5
        assert response.latency_ms == 100.0

    def test_error_response(self):
        """Test creating an error response."""
        response = LLMResponse(
            text="",
            error="API Error",
            error_traceback="Traceback: ...",
        )
        assert response.text == ""
        assert response.error == "API Error"


class TestProviderFactory:
    """Tests for provider factory."""

    def test_create_anthropic_provider(self):
        """Test creating Anthropic provider."""
        with patch(
            "tool_factory.providers.anthropic.AnthropicProvider._initialize_client"
        ):
            provider = create_provider(
                provider=LLMProviderEnum.ANTHROPIC,
                api_key="test-key",
                model="claude-sonnet-4-20250514",
            )
            assert provider.provider_name == "Anthropic"
            assert provider.model == "claude-sonnet-4-20250514"

    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        with patch("tool_factory.providers.openai.OpenAIProvider._initialize_client"):
            provider = create_provider(
                provider=LLMProviderEnum.OPENAI,
                api_key="test-key",
                model="gpt-4",
            )
            assert provider.provider_name == "OpenAI"
            assert provider.model == "gpt-4"

    def test_create_google_provider(self):
        """Test creating Google provider."""
        with patch("tool_factory.providers.google.GoogleProvider._initialize_client"):
            provider = create_provider(
                provider=LLMProviderEnum.GOOGLE,
                api_key="test-key",
                model="gemini-pro",
            )
            assert provider.provider_name == "Google"
            assert provider.model == "gemini-pro"

    def test_create_provider_from_string(self):
        """Test creating provider from string."""
        with patch(
            "tool_factory.providers.anthropic.AnthropicProvider._initialize_client"
        ):
            provider = create_provider(
                provider="anthropic",
                api_key="test-key",
                model="test-model",
            )
            assert provider.provider_name == "Anthropic"

    def test_invalid_provider_raises(self):
        """Test that invalid provider raises error."""
        with pytest.raises(ValueError, match="not a valid"):
            create_provider(
                provider="invalid-provider",
                api_key="test-key",
                model="test-model",
            )


class TestBaseLLMProvider:
    """Tests for base provider functionality."""

    def test_call_with_error_returns_error_response(self):
        """Test that errors are captured in response."""

        class FailingProvider(BaseLLMProvider):
            def _initialize_client(self):
                pass

            def _call_api(self, system_prompt, user_prompt, max_tokens):
                raise RuntimeError("Test error")

        provider = FailingProvider(api_key="test", model="test")
        response = provider.call("system", "user")

        assert response.text == ""
        assert response.error == "Test error"
        assert response.error_traceback is not None
        assert "RuntimeError" in response.error_traceback

    def test_call_measures_latency(self):
        """Test that latency is measured."""

        class SlowProvider(BaseLLMProvider):
            def _initialize_client(self):
                pass

            def _call_api(self, system_prompt, user_prompt, max_tokens):
                import time

                time.sleep(0.01)  # 10ms
                return LLMResponse(text="OK")

        provider = SlowProvider(api_key="test", model="test")
        response = provider.call("system", "user")

        assert response.latency_ms >= 10  # At least 10ms

    def test_provider_name(self):
        """Test provider name property."""

        class MyCustomProvider(BaseLLMProvider):
            def _initialize_client(self):
                pass

            def _call_api(self, system_prompt, user_prompt, max_tokens):
                return LLMResponse(text="OK")

        provider = MyCustomProvider(api_key="test", model="test")
        assert provider.provider_name == "MyCustom"
