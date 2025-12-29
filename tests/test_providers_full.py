"""Full tests for provider implementations."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from tool_factory.providers.base import LLMResponse, BaseLLMProvider
from tool_factory.providers.factory import create_provider
from tool_factory.config import LLMProvider


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    def test_provider_creation(self):
        """Test AnthropicProvider can be created."""
        from tool_factory.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider(api_key="test-key", model="claude-3")
        assert provider.model == "claude-3"
        assert provider.api_key == "test-key"
        assert provider.provider_name == "Anthropic"

    def test_call_method(self):
        """Test call method with mocked client."""
        from tool_factory.providers.anthropic import AnthropicProvider

        # Create provider
        provider = AnthropicProvider(api_key="test-key", model="claude-3")

        # Mock the client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Generated response")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.model = "claude-3"
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response
        provider._client = mock_client

        # Call the method
        result = provider.call(
            system_prompt="You are helpful",
            user_prompt="Hello",
            max_tokens=100,
        )

        assert isinstance(result, LLMResponse)
        assert result.text == "Generated response"
        assert result.tokens_in == 100
        assert result.tokens_out == 50

    def test_call_with_exception(self):
        """Test call method handles exception from client."""
        from tool_factory.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider(api_key="test-key", model="claude-3")

        # Mock client to raise exception
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API Error")
        provider._client = mock_client

        # Call should return response with error
        result = provider.call("System", "User", max_tokens=100)
        assert isinstance(result, LLMResponse)
        assert result.error is not None


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    def test_provider_creation(self):
        """Test OpenAIProvider can be created."""
        from tool_factory.providers.openai import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key", model="gpt-4")
        assert provider.model == "gpt-4"
        assert provider.provider_name == "OpenAI"

    def test_call_method(self):
        """Test call method with mocked client."""
        from tool_factory.providers.openai import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key", model="gpt-4")

        # Mock the client
        mock_client = Mock()
        mock_message = Mock()
        mock_message.content = "OpenAI response"
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50)
        mock_response.id = "chatcmpl-123"
        mock_response.model = "gpt-4"
        mock_response.object = "chat.completion"
        mock_client.chat.completions.create.return_value = mock_response
        provider._client = mock_client

        result = provider.call("System", "User", max_tokens=100)

        assert isinstance(result, LLMResponse)
        assert result.text == "OpenAI response"
        assert result.tokens_in == 100
        assert result.tokens_out == 50


class TestGoogleProvider:
    """Tests for GoogleProvider."""

    def test_provider_creation(self):
        """Test GoogleProvider can be created."""
        from tool_factory.providers.google import GoogleProvider

        provider = GoogleProvider(api_key="test-key", model="gemini-pro")
        assert provider.model == "gemini-pro"
        assert provider.provider_name == "Google"

    def test_call_method(self):
        """Test call method with mocked client."""
        from tool_factory.providers.google import GoogleProvider

        provider = GoogleProvider(api_key="test-key", model="gemini-pro")

        # Mock the generative model
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Google response"
        mock_response.candidates = []
        mock_response.prompt_feedback = None
        mock_model.generate_content.return_value = mock_response
        provider._client = mock_model

        result = provider.call("System", "User", max_tokens=100)

        assert isinstance(result, LLMResponse)
        assert result.text == "Google response"


class TestClaudeCodeProvider:
    """Tests for ClaudeCodeProvider."""

    def test_provider_creation(self):
        """Test ClaudeCodeProvider can be created."""
        from tool_factory.providers.claude_code import ClaudeCodeProvider

        provider = ClaudeCodeProvider(api_key="oauth-token", model="claude-3")
        assert provider.provider_name == "ClaudeCode"

    def test_initialize_client_sets_env(self):
        """Test that _initialize_client sets environment variable."""
        from tool_factory.providers.claude_code import ClaudeCodeProvider
        import os

        provider = ClaudeCodeProvider(api_key="my-token", model="claude-3")
        provider._initialize_client()

        assert os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") == "my-token"
        assert provider._client is True


class TestProviderFactory:
    """Tests for provider factory."""

    def test_create_anthropic_provider(self):
        """Test creating Anthropic provider."""
        provider = create_provider(
            provider=LLMProvider.ANTHROPIC,
            api_key="test-key",
            model="claude-3",
        )

        from tool_factory.providers.anthropic import AnthropicProvider

        assert isinstance(provider, AnthropicProvider)

    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        provider = create_provider(
            provider=LLMProvider.OPENAI,
            api_key="test-key",
            model="gpt-4",
        )

        from tool_factory.providers.openai import OpenAIProvider

        assert isinstance(provider, OpenAIProvider)

    def test_create_google_provider(self):
        """Test creating Google provider."""
        provider = create_provider(
            provider=LLMProvider.GOOGLE,
            api_key="test-key",
            model="gemini-pro",
        )

        from tool_factory.providers.google import GoogleProvider

        assert isinstance(provider, GoogleProvider)

    def test_create_claude_code_provider(self):
        """Test creating Claude Code provider."""
        provider = create_provider(
            provider=LLMProvider.CLAUDE_CODE,
            api_key="oauth-token",
            model="claude-3",
        )

        from tool_factory.providers.claude_code import ClaudeCodeProvider

        assert isinstance(provider, ClaudeCodeProvider)

    def test_factory_with_temperature(self):
        """Test factory passes temperature."""
        provider = create_provider(
            provider=LLMProvider.ANTHROPIC,
            api_key="test-key",
            model="claude-3",
            temperature=0.7,
        )

        assert provider.temperature == 0.7


class TestBaseLLMProvider:
    """Tests for BaseLLMProvider base class."""

    def test_is_abstract(self):
        """Test that BaseLLMProvider is abstract."""
        from abc import ABC

        assert issubclass(BaseLLMProvider, ABC)

    def test_cannot_instantiate(self):
        """Test that BaseLLMProvider cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseLLMProvider(api_key="test", model="test")

    def test_has_required_methods(self):
        """Test that BaseLLMProvider has required abstract methods."""
        assert hasattr(BaseLLMProvider, "_initialize_client")
        assert hasattr(BaseLLMProvider, "_call_api")
        assert hasattr(BaseLLMProvider, "call")

    def test_provider_name_property(self):
        """Test provider_name property is required."""
        assert hasattr(BaseLLMProvider, "provider_name")


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_create_minimal(self):
        """Test creating minimal LLMResponse."""
        response = LLMResponse(
            text="Hello",
            tokens_in=10,
            tokens_out=5,
            model="test",
            raw_response=None,
        )

        assert response.text == "Hello"
        assert response.error is None

    def test_create_full(self):
        """Test creating full LLMResponse."""
        response = LLMResponse(
            text="Response text",
            tokens_in=100,
            tokens_out=50,
            model="claude-3",
            raw_response={"id": "123", "content": "Response text"},
            error=None,
        )

        assert response.text == "Response text"
        assert response.tokens_in == 100
        assert response.tokens_out == 50
        assert response.raw_response is not None

    def test_create_with_error(self):
        """Test creating LLMResponse with error."""
        response = LLMResponse(
            text="",
            tokens_in=0,
            tokens_out=0,
            model="test",
            raw_response=None,
            error="API Error: Rate limited",
        )

        assert response.error == "API Error: Rate limited"

    def test_none_token_counts(self):
        """Test LLMResponse with None token counts."""
        response = LLMResponse(
            text="Response",
            tokens_in=None,
            tokens_out=None,
            model="test",
            raw_response=None,
        )

        assert response.tokens_in is None
        assert response.tokens_out is None


class TestProviderCallWithLogger:
    """Tests for provider call with execution logger."""

    def test_call_with_logger(self):
        """Test that call logs to execution logger."""
        from tool_factory.providers.anthropic import AnthropicProvider
        from tool_factory.execution_logger import ExecutionLogger

        provider = AnthropicProvider(api_key="test-key", model="claude-3")

        # Create a logger
        logger = ExecutionLogger("Test", "anthropic", "claude-3")

        # Mock the client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.model = "claude-3"
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response
        provider._client = mock_client

        # Call without logger (logger is handled at agent level, not provider level)
        result = provider.call(
            system_prompt="System",
            user_prompt="User",
            max_tokens=100,
        )

        assert isinstance(result, LLMResponse)
        assert result.text == "Response"
