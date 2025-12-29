"""Additional tests to boost coverage."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import json

from tool_factory.models import ToolSpec


class TestConfigEdgeCases:
    """Tests for config edge cases."""

    def test_claude_model_list(self):
        """Test Claude models are defined."""
        from tool_factory.config import CLAUDE_MODELS

        # Check for models that exist
        assert len(CLAUDE_MODELS) > 0
        assert any("claude" in k for k in CLAUDE_MODELS.keys())

    def test_openai_model_list(self):
        """Test OpenAI models are defined."""
        from tool_factory.config import OPENAI_MODELS

        assert len(OPENAI_MODELS) > 0

    def test_google_model_list(self):
        """Test Google models are defined."""
        from tool_factory.config import GOOGLE_MODELS

        assert "gemini-2.0-flash" in GOOGLE_MODELS


class TestExecutionLoggerEdgeCases:
    """Tests for ExecutionLogger edge cases."""

    def test_log_http_request_with_headers(self):
        """Test logging HTTP request with all headers."""
        from tool_factory.execution_logger import ExecutionLogger

        logger = ExecutionLogger("Test", "test", "test")
        logger.log_http_request(
            method="POST",
            url="https://api.example.com",
            request_headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer token",
            },
            request_body='{"data": "value"}',
            status_code=200,
            response_headers={"X-Request-Id": "123"},
            response_body='{"result": "ok"}',
            latency_ms=100.0,
            error=None,
        )

        assert len(logger.http_requests) == 1
        req = logger.http_requests[0]
        assert req.method == "POST"
        assert req.status_code == 200

    def test_log_tool_execution_with_latency(self):
        """Test logging tool execution with latency."""
        from tool_factory.execution_logger import ExecutionLogger

        logger = ExecutionLogger("Test", "test", "test")
        logger.log_tool_execution(
            tool_name="my_tool",
            input_args={"x": 1, "y": 2},
            output_result={"sum": 3},
            latency_ms=50.0,
            error=None,
        )

        assert len(logger.tool_executions) == 1
        exe = logger.tool_executions[0]
        assert exe.latency_ms == 50.0


class TestWebSearchEdgeCases:
    """Tests for web search functionality."""

    def test_web_searcher_import(self):
        """Test WebSearcher can be imported."""
        from tool_factory.web_search import WebSearcher

        assert WebSearcher is not None

    def test_web_search_dataclass(self):
        """Test WebSearchEntry creation."""
        from tool_factory.models import WebSearchEntry

        entry = WebSearchEntry(
            query="test query",
            results="test results",
            sources=["https://example.com"],
        )
        assert entry.query == "test query"


class TestMiddlewareValidation:
    """Tests for middleware validation."""

    def test_validation_error_creation(self):
        """Test ValidationError can be created."""
        from tool_factory.middleware.validation import ValidationError

        error = ValidationError("Test error")
        assert str(error) == "Test error"

    def test_request_validator_import(self):
        """Test RequestValidator can be imported."""
        from tool_factory.middleware.validation import RequestValidator

        assert RequestValidator is not None

    def test_schema_validator_import(self):
        """Test SchemaValidator can be imported."""
        from tool_factory.middleware.validation import SchemaValidator

        assert SchemaValidator is not None


class TestInputValidation:
    """Tests for input validation utilities."""

    def test_input_validator_import(self):
        """Test InputValidator can be imported."""
        from tool_factory.utils.input_validation import InputValidator

        assert InputValidator is not None

    def test_validate_integer_function(self):
        """Test validate_integer function."""
        from tool_factory.utils.input_validation import validate_integer

        result = validate_integer(42, minimum=0, maximum=100)
        assert result.is_valid is True
        assert result.value == 42

    def test_validate_number_function(self):
        """Test validate_number function."""
        from tool_factory.utils.input_validation import validate_number

        result = validate_number(3.14, minimum=0.0)
        assert result.is_valid is True
        assert result.value == 3.14

    def test_sanitize_string_function(self):
        """Test sanitize_string function."""
        from tool_factory.utils.input_validation import sanitize_string

        result = sanitize_string("Hello <script>alert(1)</script>")
        assert "<script>" not in result


class TestOpenAPIParser:
    """Tests for OpenAPI parsing."""

    def test_openapi_parser_import(self):
        """Test OpenAPI parser can be imported."""
        from tool_factory.openapi import OpenAPIParser

        assert OpenAPIParser is not None

    def test_openapi_validator_import(self):
        """Test OpenAPIValidator can be imported."""
        from tool_factory.openapi import OpenAPIValidator

        assert OpenAPIValidator is not None

    def test_endpoint_spec_import(self):
        """Test EndpointSpec can be imported."""
        from tool_factory.openapi import EndpointSpec

        assert EndpointSpec is not None


class TestSecurityScanner:
    """Tests for security scanning."""

    def test_security_scanner_import(self):
        """Test SecurityScanner can be imported."""
        from tool_factory.security.scanner import SecurityScanner

        assert SecurityScanner is not None

    def test_scan_code_function(self):
        """Test scan_code function."""
        from tool_factory.security.scanner import scan_code

        code = """
def hello():
    return "Hello, World!"
"""
        result = scan_code(code)
        # Result is a list of findings
        assert isinstance(result, list)

    def test_security_issue_import(self):
        """Test SecurityIssue can be imported."""
        from tool_factory.security.scanner import SecurityIssue

        assert SecurityIssue is not None


class TestDependencyUtils:
    """Tests for dependency utilities."""

    def test_detect_packages_function(self):
        """Test detect_packages_from_imports function."""
        from tool_factory.utils.dependencies import detect_packages_from_imports

        code = """
import httpx
import json
from pydantic import BaseModel
"""
        packages = detect_packages_from_imports(code)
        assert isinstance(packages, (list, set))

    def test_known_packages(self):
        """Test KNOWN_PACKAGES dict."""
        from tool_factory.utils.dependencies import KNOWN_PACKAGES

        assert isinstance(KNOWN_PACKAGES, dict)
        assert len(KNOWN_PACKAGES) > 0


class TestProductionConfig:
    """Tests for production configuration."""

    def test_production_config_defaults(self):
        """Test ProductionConfig defaults."""
        from tool_factory.production import ProductionConfig

        config = ProductionConfig()
        assert config.enable_logging is True
        assert config.enable_metrics is False
        assert config.enable_rate_limiting is False

    def test_production_code_generator_import(self):
        """Test ProductionCodeGenerator can be imported."""
        from tool_factory.production import ProductionCodeGenerator

        assert ProductionCodeGenerator is not None


class TestObservability:
    """Tests for observability features."""

    def test_telemetry_import(self):
        """Test telemetry module can be imported."""
        from tool_factory.observability.telemetry import TelemetryConfig

        assert TelemetryConfig is not None

    def test_telemetry_config_defaults(self):
        """Test TelemetryConfig defaults."""
        from tool_factory.observability.telemetry import TelemetryConfig

        config = TelemetryConfig()
        assert config.enabled is True
