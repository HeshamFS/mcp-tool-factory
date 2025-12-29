"""Tests for Claude Code provider."""

import pytest
from unittest.mock import Mock, patch
import os

from tool_factory.providers.claude_code import ClaudeCodeProvider
from tool_factory.providers.base import LLMResponse


class TestClaudeCodeProviderInit:
    """Tests for ClaudeCodeProvider initialization."""

    def test_init_sets_env_var(self):
        """Test that init sets CLAUDE_CODE_OAUTH_TOKEN env var."""
        provider = ClaudeCodeProvider(
            api_key="test-oauth-token",
            model="claude-agent-sdk",
        )
        provider._initialize_client()
        assert os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") == "test-oauth-token"

    def test_init_sets_client_flag(self):
        """Test that init sets client flag."""
        provider = ClaudeCodeProvider(
            api_key="test-token",
            model="test-model",
        )
        provider._initialize_client()
        assert provider._client is True

    def test_init_stores_api_key(self):
        """Test that api_key is stored."""
        provider = ClaudeCodeProvider(
            api_key="my-api-key",
            model="test-model",
        )
        assert provider.api_key == "my-api-key"


class TestClaudeCodeProviderCallApi:
    """Tests for ClaudeCodeProvider._call_api method."""

    def test_call_api_returns_llm_response(self):
        """Test that _call_api returns proper LLMResponse."""
        provider = ClaudeCodeProvider(
            api_key="test-token",
            model="claude-agent-sdk",
        )
        provider._client = True

        with patch.object(provider, "_async_query") as mock_query:
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = "Generated response text"

                response = provider._call_api(
                    system_prompt="You are helpful.",
                    user_prompt="Hello",
                    max_tokens=1000,
                )

                assert isinstance(response, LLMResponse)
                assert response.text == "Generated response text"
                assert response.model == "claude-agent-sdk"

    def test_call_api_tokens_are_none(self):
        """Test that token counts are None (SDK doesn't expose them)."""
        provider = ClaudeCodeProvider(
            api_key="test-token",
            model="claude-agent-sdk",
        )
        provider._client = True

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = "response"

            response = provider._call_api(
                system_prompt="System",
                user_prompt="User",
                max_tokens=1000,
            )

            assert response.tokens_in is None
            assert response.tokens_out is None


class TestClaudeCodeProviderIntegration:
    """Integration tests for ClaudeCodeProvider."""

    def test_provider_has_required_attributes(self):
        """Test that provider has required attributes."""
        provider = ClaudeCodeProvider(
            api_key="test-token",
            model="claude-agent-sdk",
        )

        assert hasattr(provider, "api_key")
        assert hasattr(provider, "model")
        assert hasattr(provider, "call")
        assert hasattr(provider, "_call_api")
        assert hasattr(provider, "_initialize_client")
        assert hasattr(provider, "_async_query")

    def test_call_method_works_with_mock(self):
        """Test the public call method with mocking."""
        provider = ClaudeCodeProvider(
            api_key="test-token",
            model="claude-agent-sdk",
        )
        provider._client = True

        with patch.object(provider, "_call_api") as mock_call:
            mock_call.return_value = LLMResponse(
                text="Test response",
                tokens_in=None,
                tokens_out=None,
                model="claude-agent-sdk",
                raw_response=None,
            )

            response = provider.call(
                system_prompt="System",
                user_prompt="User",
                max_tokens=1000,
            )

            assert response.text == "Test response"
            mock_call.assert_called_once()
