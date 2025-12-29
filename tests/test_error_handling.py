"""Tests for error handling across the codebase."""

import pytest
from unittest.mock import Mock
import tempfile
from pathlib import Path


class TestValidationErrorHandling:
    """Tests for validation utilities error handling."""

    def test_validate_none_value(self):
        """Test validation of None values."""
        from tool_factory.utils.input_validation import (
            validate_string,
            validate_integer,
            validate_number,
        )

        result = validate_string(None, "test")
        assert not result.is_valid

        result = validate_integer(None, "test")
        assert not result.is_valid

        result = validate_number(None, "test")
        assert not result.is_valid

    def test_validate_wrong_type(self):
        """Test validation of wrong types."""
        from tool_factory.utils.input_validation import validate_integer

        result = validate_integer("not an int", "test")
        assert not result.is_valid

    def test_validate_string_length(self):
        """Test validation of string length."""
        from tool_factory.utils.input_validation import validate_string

        result = validate_string("ab", "test", min_length=5)
        assert not result.is_valid

        result = validate_string("abcdefghij", "test", max_length=5)
        assert not result.is_valid

    def test_validate_malformed_url(self):
        """Test validation of malformed URLs."""
        from tool_factory.utils.input_validation import validate_url

        result = validate_url("not-a-url", "test")
        assert not result.is_valid

    def test_validate_malformed_email(self):
        """Test validation of malformed emails."""
        from tool_factory.utils.input_validation import validate_email

        result = validate_email("not-an-email", "test")
        assert not result.is_valid

    def test_validate_path_traversal(self):
        """Test validation blocks path traversal."""
        from tool_factory.utils.input_validation import validate_path

        # Path traversal should be blocked by default
        result = validate_path("../../../etc/passwd", "test")
        assert not result.is_valid

    def test_sanitize_xss_attempt(self):
        """Test sanitization of XSS attempts."""
        from tool_factory.utils.input_validation import sanitize_string

        result = sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result

    def test_validate_finite(self):
        """Test validation of finite numbers."""
        from tool_factory.utils.input_validation import validate_finite
        import math

        result = validate_finite(math.inf, "test")
        assert not result.is_valid

        result = validate_finite(math.nan, "test")
        assert not result.is_valid

        result = validate_finite(42.0, "test")
        assert result.is_valid


class TestSecurityScannerErrorHandling:
    """Tests for security scanner error handling."""

    def test_scan_invalid_file(self):
        """Test scanning invalid file path."""
        from tool_factory.security import scan_file

        issues = scan_file("/nonexistent/file.py")
        assert issues == []

    def test_scan_binary_file(self):
        """Test scanning binary file."""
        from tool_factory.security import scan_file

        # Create temp binary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as f:
            f.write(b"\x00\x01\x02\x03")
            temp_path = f.name

        try:
            issues = scan_file(temp_path)
            # Should handle gracefully (may find issues or not)
            assert isinstance(issues, list)
        finally:
            Path(temp_path).unlink()

    def test_scan_empty_file(self):
        """Test scanning empty file."""
        from tool_factory.security import scan_file

        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as f:
            temp_path = f.name

        try:
            issues = scan_file(temp_path)
            assert issues == []
        finally:
            Path(temp_path).unlink()


class TestOpenAPIErrorHandling:
    """Tests for error handling in OpenAPI processing."""

    def test_parser_empty_paths(self):
        """Test OpenAPI parser with empty paths."""
        from tool_factory.openapi import OpenAPIParser

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {},
        }
        parser = OpenAPIParser(spec)
        endpoints = parser.get_endpoints()
        assert len(endpoints) == 0


class TestProductionErrorHandling:
    """Tests for production features error handling."""

    def test_rate_limit_backend_enum(self):
        """Test RateLimitBackend enum values."""
        from tool_factory.production import RateLimitBackend

        assert RateLimitBackend.MEMORY.value == "memory"
        assert RateLimitBackend.REDIS.value == "redis"


class TestMiddlewareErrorHandling:
    """Tests for middleware error handling."""

    def test_validation_type_enum(self):
        """Test ValidationType enum."""
        from tool_factory.middleware.validation import ValidationType

        assert ValidationType.REQUEST.value == "request"
        assert ValidationType.RESPONSE.value == "response"


class TestAuthErrorHandling:
    """Tests for authentication error handling."""

    def test_pkce_verifier_generation(self):
        """Test PKCE verifier generation."""
        from tool_factory.auth.pkce import generate_code_verifier

        verifier = generate_code_verifier()
        assert len(verifier) >= 43
        assert len(verifier) <= 128

    def test_pkce_challenge_generation(self):
        """Test PKCE challenge generation."""
        from tool_factory.auth.pkce import (
            generate_code_verifier,
            generate_code_challenge,
        )

        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        assert len(challenge) > 0

    def test_oauth_token_expiry(self):
        """Test OAuth2 token expiry detection."""
        from tool_factory.auth.oauth2 import OAuth2Token

        # Token with negative expiry is expired
        token = OAuth2Token(
            access_token="test",
            token_type="Bearer",
            expires_in=-1,
        )
        assert token.is_expired

    def test_oauth_token_valid(self):
        """Test OAuth2 token valid detection."""
        from tool_factory.auth.oauth2 import OAuth2Token

        token = OAuth2Token(
            access_token="test",
            token_type="Bearer",
            expires_in=3600,
        )
        assert not token.is_expired


class TestTelemetryErrorHandling:
    """Tests for telemetry error handling."""

    def test_telemetry_exporter_enum(self):
        """Test TelemetryExporter enum values."""
        from tool_factory.observability.telemetry import TelemetryExporter

        assert TelemetryExporter.OTLP.value == "otlp"
        assert TelemetryExporter.CONSOLE.value == "console"


class TestDependencyErrorHandling:
    """Tests for dependency versioning error handling."""

    def test_unknown_package(self):
        """Test handling of unknown package."""
        from tool_factory.utils.dependencies import get_package_version

        result = get_package_version("completely_unknown_pkg_xyz")
        assert ">=0.1.0" in result

    def test_detect_from_empty_code(self):
        """Test package detection from empty code."""
        from tool_factory.utils.dependencies import detect_packages_from_imports

        packages = detect_packages_from_imports("")
        assert packages == []

    def test_detect_from_invalid_python(self):
        """Test package detection from invalid Python code."""
        from tool_factory.utils.dependencies import detect_packages_from_imports

        # Invalid Python syntax
        packages = detect_packages_from_imports("this is not valid python {{{")
        # Should return empty or handle gracefully
        assert isinstance(packages, list)


class TestProviderErrorRecovery:
    """Tests for provider error recovery mechanisms."""

    def test_anthropic_error_in_response(self):
        """Test Anthropic provider handles API errors."""
        from tool_factory.providers import AnthropicProvider

        provider = AnthropicProvider(
            api_key="test-key",
            model="claude-3-opus",
        )

        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API Error")
        provider._client = mock_client

        response = provider.call("system", "user")
        assert response.error is not None
        assert response.text == ""

    def test_openai_error_in_response(self):
        """Test OpenAI provider handles API errors."""
        from tool_factory.providers import OpenAIProvider

        provider = OpenAIProvider(
            api_key="test-key",
            model="gpt-4",
        )

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        provider._client = mock_client

        response = provider.call("system", "user")
        assert response.error is not None
        assert response.text == ""

    def test_google_error_in_response(self):
        """Test Google provider handles API errors."""
        from tool_factory.providers import GoogleProvider

        provider = GoogleProvider(
            api_key="test-key",
            model="gemini-pro",
        )

        mock_client = Mock()
        mock_client.generate_content.side_effect = Exception("API Error")
        provider._client = mock_client

        response = provider.call("system", "user")
        assert response.error is not None
        assert response.text == ""

    def test_error_includes_traceback(self):
        """Test errors include traceback."""
        from tool_factory.providers import AnthropicProvider

        provider = AnthropicProvider(
            api_key="test-key",
            model="claude-3-opus",
        )

        mock_client = Mock()
        mock_client.messages.create.side_effect = ValueError("Test Error")
        provider._client = mock_client

        response = provider.call("system", "user")
        assert response.error_traceback is not None
        assert "ValueError" in response.error_traceback
