"""Tests for LLM providers with mocking."""

from unittest.mock import Mock

import pytest

from tool_factory.providers import (
    AnthropicProvider,
    BaseLLMProvider,
    ClaudeCodeProvider,
    GoogleProvider,
    LLMResponse,
    OpenAIProvider,
    create_provider,
)


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_successful_response(self):
        """Test successful response."""
        response = LLMResponse(
            text="Hello, world!",
            model="test-model",
            tokens_in=10,
            tokens_out=5,
            latency_ms=100.0,
        )
        assert response.text == "Hello, world!"
        assert response.error is None
        assert response.tokens_in == 10

    def test_error_response(self):
        """Test error response."""
        response = LLMResponse(
            text="",
            model="test-model",
            error="API error",
            error_traceback="Traceback...",
        )
        assert response.error == "API error"
        assert response.error_traceback == "Traceback..."


class TestCreateProvider:
    """Tests for create_provider factory."""

    def test_create_anthropic(self):
        """Test creating Anthropic provider."""
        provider = create_provider(
            provider="anthropic",
            api_key="test-key",
            model="claude-3-opus-20240229",
        )
        assert isinstance(provider, AnthropicProvider)

    def test_create_openai(self):
        """Test creating OpenAI provider."""
        provider = create_provider(
            provider="openai",
            api_key="test-key",
            model="gpt-4",
        )
        assert isinstance(provider, OpenAIProvider)

    def test_create_google(self):
        """Test creating Google provider."""
        provider = create_provider(
            provider="google",
            api_key="test-key",
            model="gemini-pro",
        )
        assert isinstance(provider, GoogleProvider)

    def test_create_claude_code(self):
        """Test creating Claude Code provider."""
        provider = create_provider(
            provider="claude_code",  # Note: underscore, not hyphen
            api_key="",
            model="claude-3-opus",
        )
        assert isinstance(provider, ClaudeCodeProvider)

    def test_invalid_provider(self):
        """Test invalid provider raises error."""
        with pytest.raises(ValueError, match="not a valid"):
            create_provider(
                provider="invalid-provider",
                api_key="test-key",
                model="test-model",
            )

    def test_enum_style(self):
        """Test provider can use enum."""
        from tool_factory.config import LLMProvider as LLMProviderEnum

        provider = create_provider(
            provider=LLMProviderEnum.ANTHROPIC,
            api_key="test-key",
            model="claude-3-opus-20240229",
        )
        assert isinstance(provider, AnthropicProvider)


class TestAnthropicProviderMocked:
    """Tests for AnthropicProvider with mocked API."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        return AnthropicProvider(
            api_key="test-api-key",
            model="claude-3-opus-20240229",
            temperature=0.7,
        )

    def test_call_success(self, provider):
        """Test successful API call."""
        mock_response = Mock()
        mock_response.content = [Mock(text="Generated response")]
        mock_response.model = "claude-3-opus-20240229"
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.stop_reason = "end_turn"

        # Mock the client before it's used
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        provider._client = mock_client

        response = provider.call(
            system_prompt="You are helpful.",
            user_prompt="Hello",
            max_tokens=1000,
        )

        assert response.text == "Generated response"
        assert response.error is None
        assert response.tokens_in == 100
        assert response.tokens_out == 50

    def test_call_api_error(self, provider):
        """Test API error handling."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API Error")
        provider._client = mock_client

        response = provider.call(
            system_prompt="You are helpful.",
            user_prompt="Hello",
            max_tokens=1000,
        )

        assert response.error is not None
        assert "API Error" in response.error


class TestOpenAIProviderMocked:
    """Tests for OpenAIProvider with mocked API."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        return OpenAIProvider(
            api_key="test-api-key",
            model="gpt-4",
            temperature=0.7,
        )

    def test_call_success(self, provider):
        """Test successful API call."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="OpenAI response"))]
        mock_response.model = "gpt-4"
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50)

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        provider._client = mock_client

        response = provider.call(
            system_prompt="You are helpful.",
            user_prompt="Hello",
            max_tokens=1000,
        )

        assert response.text == "OpenAI response"
        assert response.error is None

    def test_call_with_empty_response(self, provider):
        """Test handling empty response."""
        mock_response = Mock()
        mock_response.choices = []
        mock_response.model = "gpt-4"
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=0)

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        provider._client = mock_client

        response = provider.call(
            system_prompt="You are helpful.",
            user_prompt="Hello",
            max_tokens=1000,
        )

        assert response.text == ""


class TestGoogleProviderMocked:
    """Tests for GoogleProvider with mocked API."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        return GoogleProvider(
            api_key="test-api-key",
            model="gemini-pro",
            temperature=0.7,
        )

    def test_call_success(self, provider):
        """Test successful API call."""
        mock_response = Mock()
        mock_response.text = "Google response"
        mock_response.candidates = []
        mock_response.prompt_feedback = None

        mock_client = Mock()
        mock_client.generate_content.return_value = mock_response
        provider._client = mock_client

        response = provider.call(
            system_prompt="You are helpful.",
            user_prompt="Hello",
            max_tokens=1000,
        )

        assert response.text == "Google response"
        assert response.error is None


class TestClaudeCodeProviderMocked:
    """Tests for ClaudeCodeProvider with mocked SDK."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        return ClaudeCodeProvider(
            api_key="test-token",
            model="claude-3-opus",
            temperature=0.7,
        )

    def test_call_success(self, provider):
        """Test successful Claude Code call."""

        # Mock the entire _async_query method
        async def mock_async_query(system_prompt, user_prompt):
            return "Claude Code response"

        provider._client = True  # Mark as initialized
        provider._async_query = mock_async_query

        response = provider.call(
            system_prompt="You are helpful.",
            user_prompt="Hello",
            max_tokens=1000,
        )

        assert response.text == "Claude Code response"
        assert response.error is None

    def test_call_with_sdk_error(self, provider):
        """Test SDK error handling."""

        async def mock_async_query(system_prompt, user_prompt):
            raise RuntimeError("SDK not available")

        provider._client = True
        provider._async_query = mock_async_query

        response = provider.call(
            system_prompt="You are helpful.",
            user_prompt="Hello",
            max_tokens=1000,
        )

        assert response.error is not None
        assert "SDK not available" in response.error


class TestProviderInterface:
    """Tests for provider interface compliance."""

    @pytest.fixture(params=["anthropic", "openai", "google", "claude_code"])
    def provider(self, request):
        """Create each provider type."""
        return create_provider(
            provider=request.param,
            api_key="test-key",
            model="test-model",
        )

    def test_has_call_method(self, provider):
        """Test provider has call method."""
        assert hasattr(provider, "call")
        assert callable(provider.call)

    def test_inherits_from_base(self, provider):
        """Test provider inherits from BaseLLMProvider."""
        assert isinstance(provider, BaseLLMProvider)

    def test_has_required_attributes(self, provider):
        """Test provider has required attributes."""
        assert hasattr(provider, "api_key")
        assert hasattr(provider, "model")
        assert hasattr(provider, "temperature")

    def test_provider_name_property(self, provider):
        """Test provider_name property."""
        assert hasattr(provider, "provider_name")
        assert isinstance(provider.provider_name, str)
        assert len(provider.provider_name) > 0
