"""Comprehensive tests for providers module."""

import pytest
from unittest.mock import Mock, patch
import sys

from tool_factory.providers.base import LLMResponse, BaseLLMProvider


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_create_response(self):
        """Test creating LLMResponse."""
        response = LLMResponse(
            text="Hello world",
            tokens_in=100,
            tokens_out=50,
            model="test-model",
            raw_response={"id": "123"},
        )

        assert response.text == "Hello world"
        assert response.tokens_in == 100
        assert response.tokens_out == 50
        assert response.model == "test-model"
        assert response.error is None

    def test_response_with_error(self):
        """Test LLMResponse with error."""
        response = LLMResponse(
            text="",
            tokens_in=0,
            tokens_out=0,
            model="test-model",
            raw_response=None,
            error="API Error",
        )

        assert response.error == "API Error"

    def test_response_defaults(self):
        """Test LLMResponse default values."""
        response = LLMResponse(
            text="Text",
            tokens_in=10,
            tokens_out=5,
            model="model",
            raw_response=None,
        )

        assert response.error is None


class TestBaseLLMProvider:
    """Tests for BaseLLMProvider base class."""

    def test_abstract_methods(self):
        """Test that BaseLLMProvider has abstract methods."""
        assert hasattr(BaseLLMProvider, 'call')
        assert hasattr(BaseLLMProvider, 'provider_name')

    def test_is_abstract(self):
        """Test that BaseLLMProvider is abstract."""
        from abc import ABC
        assert issubclass(BaseLLMProvider, ABC)

    def test_cannot_instantiate(self):
        """Test that BaseLLMProvider cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseLLMProvider()


class TestClaudeCodeProvider:
    """Tests for Claude Code provider."""

    def test_provider_creation(self):
        """Test Claude Code provider can be created."""
        from tool_factory.providers.claude_code import ClaudeCodeProvider
        provider = ClaudeCodeProvider(api_key="token", model="claude-3")
        assert provider.model == "claude-3"
        assert provider.provider_name == "ClaudeCode"

    def test_call_returns_llm_response(self):
        """Test call returns LLMResponse."""
        from tool_factory.providers.claude_code import ClaudeCodeProvider
        provider = ClaudeCodeProvider(api_key="token", model="claude-3")
        provider._client = True

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = "Generated response"

            result = provider.call(
                system_prompt="System",
                user_prompt="User",
            )

            assert isinstance(result, LLMResponse)
            assert result.text == "Generated response"


class TestProviderFactoryImport:
    """Tests for provider factory imports."""

    def test_factory_import(self):
        """Test that factory can be imported."""
        from tool_factory.providers.factory import create_provider
        assert callable(create_provider)

    def test_factory_has_provider_mapping(self):
        """Test that factory has provider type handling."""
        from tool_factory.providers import factory
        assert hasattr(factory, 'create_provider')
