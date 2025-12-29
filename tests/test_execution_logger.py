"""Tests for execution_logger module."""

import pytest
from unittest.mock import Mock, patch
import json
import time

from tool_factory.execution_logger import (
    ExecutionLogger,
    RawLLMCall,
    RawWebSearch,
    ExecutionStep,
)


class TestExecutionLoggerInit:
    """Tests for ExecutionLogger initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        logger = ExecutionLogger(
            server_name="TestServer",
            provider="anthropic",
            model="claude-3",
        )

        assert logger.server_name == "TestServer"
        assert logger.provider == "anthropic"
        assert logger.model == "claude-3"

    def test_init_sets_defaults(self):
        """Test initialization sets default values."""
        logger = ExecutionLogger(
            server_name="Test",
            provider="test",
            model="test",
        )

        assert logger.original_description == ""
        assert logger.web_search_enabled is False
        assert logger.tools_generated == []
        assert logger.llm_calls == []
        assert logger.web_searches == []
        assert logger.steps == []


class TestExecutionLoggerLogStep:
    """Tests for log_step method."""

    def test_log_step_basic(self):
        """Test logging a step."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_step("init", "Starting")

        assert len(logger.steps) == 1
        assert logger.steps[0].step_type == "init"
        assert logger.steps[0].description == "Starting"

    def test_log_step_multiple(self):
        """Test logging multiple steps."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_step("step1", "First")
        logger.log_step("step2", "Second")
        logger.log_step("step3", "Third")

        assert len(logger.steps) == 3

    def test_log_step_with_raw_data(self):
        """Test logging a step with raw data."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_step("process", "Processing data", data={"key": "value"})

        assert len(logger.steps) == 1
        assert logger.steps[0].raw_data == {"data": {"key": "value"}}


class TestExecutionLoggerLogLLMCall:
    """Tests for log_llm_call method."""

    def test_log_llm_call_basic(self):
        """Test logging an LLM call."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")

        logger.log_llm_call(
            system_prompt="You are helpful",
            user_prompt="Hello",
            raw_response="Hi there!",
            request_params={"model": "claude-3", "max_tokens": 1000},
        )

        assert len(logger.llm_calls) == 1
        call = logger.llm_calls[0]
        assert call.system_prompt == "You are helpful"
        assert call.user_prompt == "Hello"
        assert call.raw_response == "Hi there!"

    def test_log_llm_call_with_tokens(self):
        """Test logging LLM call with token counts."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")

        logger.log_llm_call(
            system_prompt="System",
            user_prompt="User",
            raw_response="Response",
            request_params={},
            tokens_in=100,
            tokens_out=50,
            latency_ms=150.5,
        )

        call = logger.llm_calls[0]
        assert call.tokens_in == 100
        assert call.tokens_out == 50
        assert call.latency_ms == 150.5

    def test_log_llm_call_accumulates_tokens(self):
        """Test that token counts are accumulated."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")

        logger.log_llm_call("s", "u", "r", tokens_in=100, tokens_out=50)
        logger.log_llm_call("s", "u", "r", tokens_in=200, tokens_out=100)

        assert logger.total_tokens_in == 300
        assert logger.total_tokens_out == 150

    def test_log_llm_call_with_error(self):
        """Test logging LLM call with error."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")

        logger.log_llm_call(
            system_prompt="System",
            user_prompt="User",
            raw_response="",
            request_params={},
            error="API Error",
            error_traceback="Traceback...",
        )

        call = logger.llm_calls[0]
        assert call.error == "API Error"
        assert call.error_traceback == "Traceback..."


class TestExecutionLoggerLogWebSearch:
    """Tests for log_web_search method."""

    def test_log_web_search_basic(self):
        """Test logging a web search."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")

        logger.log_web_search(
            provider="anthropic",
            query="weather API",
            raw_results="Weather API docs...",
        )

        assert len(logger.web_searches) == 1
        search = logger.web_searches[0]
        assert search.provider == "anthropic"
        assert search.query == "weather API"

    def test_log_web_search_with_sources(self):
        """Test logging web search with sources."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")

        sources = [
            {"url": "https://example.com", "title": "Example"},
            {"url": "https://docs.api", "title": "API Docs"},
        ]

        logger.log_web_search(
            provider="anthropic",
            query="test",
            raw_results="results",
            sources=sources,
        )

        search = logger.web_searches[0]
        assert search.sources == sources

    def test_log_web_search_with_api_data(self):
        """Test logging web search with API request/response."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")

        logger.log_web_search(
            provider="anthropic",
            query="test",
            raw_results="results",
            api_request={"model": "claude-3"},
            api_response={"id": "123"},
            latency_ms=200.0,
        )

        search = logger.web_searches[0]
        assert search.api_request == {"model": "claude-3"}
        assert search.api_response == {"id": "123"}
        assert search.latency_ms == 200.0

    def test_log_web_search_with_error(self):
        """Test logging web search with error."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")

        logger.log_web_search(
            provider="anthropic",
            query="test",
            raw_results="",
            error="Network error",
        )

        search = logger.web_searches[0]
        assert search.error == "Network error"


class TestExecutionLoggerToJson:
    """Tests for to_json method."""

    def test_to_json_returns_valid_json(self):
        """Test to_json returns valid JSON string."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")
        logger.log_step("test", "Testing")

        json_str = logger.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["metadata"]["server_name"] == "Test"

    def test_to_json_includes_metadata(self):
        """Test to_json includes all metadata."""
        logger = ExecutionLogger("MyServer", "openai", "gpt-4")
        logger.original_description = "Test description"
        logger.web_search_enabled = True

        parsed = json.loads(logger.to_json())

        assert parsed["metadata"]["server_name"] == "MyServer"
        assert parsed["metadata"]["provider"] == "openai"
        assert parsed["metadata"]["model"] == "gpt-4"
        assert parsed["metadata"]["original_description"] == "Test description"
        assert parsed["metadata"]["web_search_enabled"] is True


class TestExecutionLoggerToMarkdown:
    """Tests for to_markdown method."""

    def test_to_markdown_basic(self):
        """Test generating markdown report."""
        logger = ExecutionLogger("TestServer", "anthropic", "claude-3")
        logger.original_description = "A test server"
        logger.tools_generated = ["tool1", "tool2"]

        md = logger.to_markdown()

        assert "# FULL Execution Log: TestServer" in md
        assert "anthropic" in md
        assert "claude-3" in md
        assert "A test server" in md

    def test_to_markdown_with_llm_calls(self):
        """Test markdown includes LLM calls."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")
        logger.log_llm_call(
            system_prompt="You are helpful",
            user_prompt="Hello world",
            raw_response="Hi there!",
            request_params={"model": "claude-3"},
            tokens_in=50,
            tokens_out=25,
        )

        md = logger.to_markdown()

        assert "LLM Call" in md

    def test_to_markdown_with_web_searches(self):
        """Test markdown includes web searches."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")
        logger.web_search_enabled = True
        logger.log_web_search(
            provider="anthropic",
            query="weather API documentation",
            raw_results="Found weather API docs",
            sources=[{"url": "https://example.com"}],
        )

        md = logger.to_markdown()

        assert "Web Search" in md

    def test_to_markdown_with_steps(self):
        """Test markdown includes execution steps."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")
        logger.log_step("init", "Initializing agent")
        logger.log_step("extract", "Extracting tool specs")
        logger.log_step("generate", "Generating code")

        md = logger.to_markdown()

        assert "Execution" in md or "Steps" in md or "Timeline" in md


class TestExecutionLoggerHttpRequests:
    """Tests for log_http_request method."""

    def test_log_http_request_basic(self):
        """Test logging an HTTP request."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_http_request(
            method="GET",
            url="https://api.example.com/users",
            status_code=200,
            response_body='{"users": []}',
        )

        assert len(logger.http_requests) == 1
        req = logger.http_requests[0]
        assert req.method == "GET"
        assert req.url == "https://api.example.com/users"
        assert req.status_code == 200

    def test_log_http_request_with_headers(self):
        """Test logging HTTP request with headers."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_http_request(
            method="POST",
            url="https://api.example.com/data",
            request_headers={"Content-Type": "application/json"},
            request_body='{"key": "value"}',
            response_headers={"X-Request-Id": "123"},
        )

        req = logger.http_requests[0]
        assert req.request_headers == {"Content-Type": "application/json"}
        assert req.request_body == '{"key": "value"}'
        assert req.response_headers == {"X-Request-Id": "123"}


class TestExecutionLoggerToolExecution:
    """Tests for log_tool_execution method."""

    def test_log_tool_execution_basic(self):
        """Test logging a tool execution."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_tool_execution(
            tool_name="get_weather",
            input_args={"city": "London"},
            output_result={"temp": 20},
        )

        assert len(logger.tool_executions) == 1
        exec = logger.tool_executions[0]
        assert exec.tool_name == "get_weather"
        assert exec.input_args == {"city": "London"}
        assert exec.output_result == {"temp": 20}

    def test_log_tool_execution_with_error(self):
        """Test logging tool execution with error."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_tool_execution(
            tool_name="failing_tool",
            input_args={},
            error="Tool failed",
        )

        exec = logger.tool_executions[0]
        assert exec.error == "Tool failed"


class TestExecutionLoggerIntegration:
    """Integration tests for ExecutionLogger."""

    def test_full_workflow(self):
        """Test a full logging workflow."""
        logger = ExecutionLogger("WeatherServer", "anthropic", "claude-3")
        logger.original_description = "Weather API server"
        logger.web_search_enabled = True

        # Log initialization
        logger.log_step("init", "Starting generation")

        # Log web search
        logger.log_web_search(
            provider="anthropic",
            query="weather API",
            raw_results="OpenWeatherMap API documentation...",
            sources=[{"url": "https://openweathermap.org/api"}],
            latency_ms=500.0,
        )

        # Log LLM call for spec extraction
        logger.log_step("extract_specs", "Extracting tool specifications")
        logger.log_llm_call(
            system_prompt="You are a tool designer",
            user_prompt="Create weather tools",
            raw_response='{"tools": [{"name": "get_weather"}]}',
            request_params={"model": "claude-3", "max_tokens": 4096},
            tokens_in=200,
            tokens_out=100,
            latency_ms=1500.0,
        )

        # Log implementation generation
        logger.log_step("implement", "Generating implementation")
        logger.log_llm_call(
            system_prompt="You are a Python developer",
            user_prompt="Implement get_weather",
            raw_response="def get_weather(city): ...",
            request_params={"model": "claude-3", "max_tokens": 2048},
            tokens_in=300,
            tokens_out=150,
            latency_ms=2000.0,
        )

        logger.tools_generated = ["get_weather"]

        # Verify JSON output
        json_str = logger.to_json()
        parsed = json.loads(json_str)
        assert parsed["metadata"]["server_name"] == "WeatherServer"
        assert parsed["metadata"]["web_search_enabled"] is True
        assert parsed["summary"]["total_llm_calls"] == 2
        assert parsed["summary"]["total_web_searches"] == 1
        assert parsed["summary"]["tools_generated"] == ["get_weather"]

        # Verify markdown output
        md = logger.to_markdown()
        assert "WeatherServer" in md
