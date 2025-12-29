"""Comprehensive tests for config module."""

import os
from unittest.mock import patch

from tool_factory.config import (
    CLAUDE_MODELS,
    DEFAULT_MODELS,
    GOOGLE_MODELS,
    OPENAI_MODELS,
    FactoryConfig,
    LLMProvider,
    get_default_config,
)


class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_provider_values(self):
        """Test enum values exist."""
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.CLAUDE_CODE.value == "claude_code"
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.GOOGLE.value == "google"


class TestModelDictionaries:
    """Tests for model dictionaries."""

    def test_claude_models_populated(self):
        """Test Claude models dict has entries."""
        assert len(CLAUDE_MODELS) > 0
        assert "claude-sonnet-4-5-20241022" in CLAUDE_MODELS

    def test_openai_models_populated(self):
        """Test OpenAI models dict has entries."""
        assert len(OPENAI_MODELS) > 0
        assert "gpt-5.2" in OPENAI_MODELS

    def test_google_models_populated(self):
        """Test Google models dict has entries."""
        assert len(GOOGLE_MODELS) > 0
        assert "gemini-2.0-flash" in GOOGLE_MODELS

    def test_default_models_for_all_providers(self):
        """Test default models exist for all providers."""
        for provider in LLMProvider:
            assert provider in DEFAULT_MODELS


class TestFactoryConfig:
    """Tests for FactoryConfig dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        config = FactoryConfig()

        assert config.provider == LLMProvider.ANTHROPIC
        assert config.max_tokens == 4096
        assert config.temperature == 0.0

    def test_provider_anthropic(self):
        """Test Anthropic provider configuration."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            config = FactoryConfig(provider=LLMProvider.ANTHROPIC)

            assert config.provider == LLMProvider.ANTHROPIC
            assert config.model == DEFAULT_MODELS[LLMProvider.ANTHROPIC]
            assert config.api_key == "test-key"

    def test_provider_openai(self):
        """Test OpenAI provider configuration."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "openai-key"}, clear=False):
            config = FactoryConfig(provider=LLMProvider.OPENAI)

            assert config.provider == LLMProvider.OPENAI
            assert config.model == DEFAULT_MODELS[LLMProvider.OPENAI]
            assert config.api_key == "openai-key"

    def test_provider_google(self):
        """Test Google provider configuration."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "google-key"}, clear=False):
            config = FactoryConfig(provider=LLMProvider.GOOGLE)

            assert config.provider == LLMProvider.GOOGLE
            assert config.model == DEFAULT_MODELS[LLMProvider.GOOGLE]
            assert config.api_key == "google-key"

    def test_provider_claude_code(self):
        """Test Claude Code provider configuration."""
        with patch.dict(
            os.environ, {"CLAUDE_CODE_OAUTH_TOKEN": "oauth-token"}, clear=False
        ):
            config = FactoryConfig(provider=LLMProvider.CLAUDE_CODE)

            assert config.provider == LLMProvider.CLAUDE_CODE
            assert config.api_key == "oauth-token"

    def test_custom_model(self):
        """Test custom model override."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "key"}, clear=False):
            config = FactoryConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-opus-4-5-20251101",
            )

            assert config.model == "claude-opus-4-5-20251101"

    def test_explicit_api_key(self):
        """Test explicit API key overrides environment."""
        config = FactoryConfig(
            provider=LLMProvider.ANTHROPIC,
            api_key="explicit-key",
        )

        assert config.api_key == "explicit-key"

    def test_custom_max_tokens(self):
        """Test custom max tokens."""
        config = FactoryConfig(max_tokens=8192)

        assert config.max_tokens == 8192

    def test_custom_temperature(self):
        """Test custom temperature."""
        config = FactoryConfig(temperature=0.7)

        assert config.temperature == 0.7


class TestFactoryConfigValidation:
    """Tests for FactoryConfig validation."""

    def test_validate_missing_api_key(self):
        """Test validation fails without API key."""
        config = FactoryConfig(api_key=None)

        errors = config.validate()

        assert len(errors) > 0
        assert any("API key" in e for e in errors)

    def test_validate_with_api_key(self):
        """Test validation passes with API key."""
        config = FactoryConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-sonnet-4-5-20241022",
            api_key="test-key",
        )

        errors = config.validate()

        # Should have no errors about API key
        assert not any("API key" in e for e in errors)

    def test_validate_unknown_anthropic_model(self):
        """Test validation fails for unknown Anthropic model."""
        config = FactoryConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-unknown-model",
            api_key="test-key",
        )

        errors = config.validate()

        assert len(errors) > 0
        assert any("Unknown Claude model" in e for e in errors)

    def test_validate_unknown_openai_model(self):
        """Test validation fails for unknown OpenAI model."""
        config = FactoryConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-unknown",
            api_key="test-key",
        )

        errors = config.validate()

        assert len(errors) > 0
        assert any("Unknown OpenAI model" in e for e in errors)

    def test_validate_unknown_google_model(self):
        """Test validation fails for unknown Google model."""
        config = FactoryConfig(
            provider=LLMProvider.GOOGLE,
            model="gemini-unknown",
            api_key="test-key",
        )

        errors = config.validate()

        assert len(errors) > 0
        assert any("Unknown Google model" in e for e in errors)

    def test_validate_claude_code_no_model_validation(self):
        """Test Claude Code provider doesn't validate model strictly."""
        config = FactoryConfig(
            provider=LLMProvider.CLAUDE_CODE,
            model="any-model",
            api_key="test-token",
        )

        errors = config.validate()

        # Should not have model validation errors for Claude Code
        assert not any("Unknown" in e for e in errors)


class TestGetDefaultConfig:
    """Tests for get_default_config function."""

    def test_prefers_claude_code_oauth(self):
        """Test Claude Code OAuth token is preferred."""
        with patch.dict(
            os.environ,
            {
                "CLAUDE_CODE_OAUTH_TOKEN": "oauth-token",
                "ANTHROPIC_API_KEY": "api-key",
            },
            clear=True,
        ):
            config = get_default_config()

            assert config.provider == LLMProvider.CLAUDE_CODE

    def test_falls_back_to_anthropic(self):
        """Test falls back to Anthropic if no OAuth token."""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "api-key"},
            clear=True,
        ):
            config = get_default_config()

            assert config.provider == LLMProvider.ANTHROPIC

    def test_falls_back_to_openai(self):
        """Test falls back to OpenAI if no Anthropic key."""
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "openai-key"},
            clear=True,
        ):
            config = get_default_config()

            assert config.provider == LLMProvider.OPENAI

    def test_falls_back_to_google(self):
        """Test falls back to Google if no other keys."""
        with patch.dict(
            os.environ,
            {"GOOGLE_API_KEY": "google-key"},
            clear=True,
        ):
            config = get_default_config()

            assert config.provider == LLMProvider.GOOGLE

    def test_default_to_claude_code_when_no_keys(self):
        """Test defaults to Claude Code when no API keys are set."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_default_config()

            assert config.provider == LLMProvider.CLAUDE_CODE
