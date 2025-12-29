"""Comprehensive tests for execution_logger module."""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch

from tool_factory.execution_logger import (
    ExecutionLogger,
    ExecutionStep,
    RawLLMCall,
    RawHTTPRequest,
    RawWebSearch,
    RawToolExecution,
)


class TestRawLLMCall:
    """Tests for RawLLMCall dataclass."""

    def test_create_basic(self):
        """Test creating basic RawLLMCall."""
        call = RawLLMCall(
            timestamp="2024-01-01T12:00:00",
            provider="anthropic",
            model="claude-3",
            system_prompt="You are a helpful assistant",
            user_prompt="Hello",
            request_params={"max_tokens": 100},
            raw_response="Hi there!",
        )

        assert call.provider == "anthropic"
        assert call.model == "claude-3"
        assert call.raw_response == "Hi there!"

    def test_create_with_tokens(self):
        """Test creating RawLLMCall with token counts."""
        call = RawLLMCall(
            timestamp="2024-01-01T12:00:00",
            provider="openai",
            model="gpt-4",
            system_prompt="System",
            user_prompt="User",
            request_params={},
            raw_response="Response",
            tokens_in=50,
            tokens_out=100,
            latency_ms=500.5,
        )

        assert call.tokens_in == 50
        assert call.tokens_out == 100
        assert call.latency_ms == 500.5

    def test_create_with_error(self):
        """Test creating RawLLMCall with error."""
        call = RawLLMCall(
            timestamp="2024-01-01T12:00:00",
            provider="anthropic",
            model="claude-3",
            system_prompt="System",
            user_prompt="User",
            request_params={},
            raw_response="",
            error="API Error: Rate limited",
            error_traceback="Traceback...",
        )

        assert call.error == "API Error: Rate limited"
        assert call.error_traceback == "Traceback..."


class TestRawHTTPRequest:
    """Tests for RawHTTPRequest dataclass."""

    def test_create_basic(self):
        """Test creating basic RawHTTPRequest."""
        req = RawHTTPRequest(
            timestamp="2024-01-01T12:00:00",
            method="GET",
            url="https://api.example.com/data",
        )

        assert req.method == "GET"
        assert req.url == "https://api.example.com/data"
        assert req.request_headers == {}
        assert req.request_body == ""

    def test_create_full(self):
        """Test creating full RawHTTPRequest."""
        req = RawHTTPRequest(
            timestamp="2024-01-01T12:00:00",
            method="POST",
            url="https://api.example.com/create",
            request_headers={"Content-Type": "application/json"},
            request_body='{"name": "test"}',
            status_code=201,
            response_headers={"X-Request-Id": "abc123"},
            response_body='{"id": 1, "name": "test"}',
            latency_ms=150.0,
        )

        assert req.status_code == 201
        assert req.response_body == '{"id": 1, "name": "test"}'
        assert req.latency_ms == 150.0

    def test_create_with_error(self):
        """Test creating RawHTTPRequest with error."""
        req = RawHTTPRequest(
            timestamp="2024-01-01T12:00:00",
            method="GET",
            url="https://api.example.com/fail",
            error="Connection timeout",
        )

        assert req.error == "Connection timeout"
        assert req.status_code is None


class TestRawWebSearch:
    """Tests for RawWebSearch dataclass."""

    def test_create_basic(self):
        """Test creating basic RawWebSearch."""
        search = RawWebSearch(
            timestamp="2024-01-01T12:00:00",
            provider="anthropic",
            query="weather API documentation",
            raw_results="Found 10 results...",
        )

        assert search.provider == "anthropic"
        assert search.query == "weather API documentation"
        assert search.sources == []

    def test_create_with_sources(self):
        """Test creating RawWebSearch with sources."""
        search = RawWebSearch(
            timestamp="2024-01-01T12:00:00",
            provider="openai",
            query="REST API best practices",
            raw_results="Multiple articles found",
            sources=[
                {"url": "https://example.com/1", "title": "Article 1"},
                {"url": "https://example.com/2", "title": "Article 2"},
            ],
            api_request={"query": "test"},
            api_response={"results": []},
            latency_ms=250.0,
        )

        assert len(search.sources) == 2
        assert search.latency_ms == 250.0


class TestRawToolExecution:
    """Tests for RawToolExecution dataclass."""

    def test_create_basic(self):
        """Test creating basic RawToolExecution."""
        exec = RawToolExecution(
            timestamp="2024-01-01T12:00:00",
            tool_name="get_weather",
        )

        assert exec.tool_name == "get_weather"
        assert exec.input_args == {}
        assert exec.output_result is None

    def test_create_full(self):
        """Test creating full RawToolExecution."""
        exec = RawToolExecution(
            timestamp="2024-01-01T12:00:00",
            tool_name="calculate",
            input_args={"a": 10, "b": 20},
            output_result={"sum": 30},
            latency_ms=5.0,
        )

        assert exec.input_args == {"a": 10, "b": 20}
        assert exec.output_result == {"sum": 30}
        assert exec.latency_ms == 5.0

    def test_create_with_error(self):
        """Test creating RawToolExecution with error."""
        exec = RawToolExecution(
            timestamp="2024-01-01T12:00:00",
            tool_name="failing_tool",
            input_args={"invalid": "data"},
            error="Invalid input format",
        )

        assert exec.error == "Invalid input format"


class TestExecutionStep:
    """Tests for ExecutionStep dataclass."""

    def test_create_basic(self):
        """Test creating basic ExecutionStep."""
        step = ExecutionStep(
            timestamp="2024-01-01T12:00:00",
            step_type="init",
            description="Initializing server generation",
        )

        assert step.step_type == "init"
        assert step.description == "Initializing server generation"
        assert step.raw_data == {}

    def test_create_with_data(self):
        """Test creating ExecutionStep with raw data."""
        step = ExecutionStep(
            timestamp="2024-01-01T12:00:00",
            step_type="generate",
            description="Generating tool implementation",
            raw_data={"tool_name": "weather", "status": "success"},
        )

        assert step.raw_data["tool_name"] == "weather"
        assert step.raw_data["status"] == "success"


class TestExecutionLoggerInit:
    """Tests for ExecutionLogger initialization."""

    def test_init_basic(self):
        """Test basic ExecutionLogger initialization."""
        logger = ExecutionLogger("TestServer", "anthropic", "claude-3")

        assert logger.server_name == "TestServer"
        assert logger.provider == "anthropic"
        assert logger.model == "claude-3"
        assert logger.original_description == ""
        assert logger.web_search_enabled is False

    def test_init_empty_lists(self):
        """Test that lists are initialized empty."""
        logger = ExecutionLogger("Test", "test", "test")

        assert logger.llm_calls == []
        assert logger.http_requests == []
        assert logger.web_searches == []
        assert logger.tool_executions == []
        assert logger.steps == []
        assert logger.tools_generated == []

    def test_init_counters(self):
        """Test that counters are initialized to zero."""
        logger = ExecutionLogger("Test", "test", "test")

        assert logger.total_tokens_in == 0
        assert logger.total_tokens_out == 0

    def test_init_has_start_time(self):
        """Test that start_time is set."""
        logger = ExecutionLogger("Test", "test", "test")

        assert logger.start_time is not None
        assert isinstance(logger.start_time, datetime)


class TestExecutionLoggerLogStep:
    """Tests for ExecutionLogger.log_step method."""

    def test_log_step_basic(self):
        """Test logging a basic step."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_step("init", "Starting generation")

        assert len(logger.steps) == 1
        assert logger.steps[0].step_type == "init"
        assert logger.steps[0].description == "Starting generation"

    def test_log_step_with_raw_data(self):
        """Test logging step with raw data."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_step("generate", "Generating code", tool_name="weather", status="ok")

        assert logger.steps[0].raw_data["tool_name"] == "weather"
        assert logger.steps[0].raw_data["status"] == "ok"

    def test_log_multiple_steps(self):
        """Test logging multiple steps."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_step("step1", "First step")
        logger.log_step("step2", "Second step")
        logger.log_step("step3", "Third step")

        assert len(logger.steps) == 3
        assert logger.steps[2].step_type == "step3"


class TestExecutionLoggerLogLLMCall:
    """Tests for ExecutionLogger.log_llm_call method."""

    def test_log_llm_call_basic(self):
        """Test logging a basic LLM call."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")

        logger.log_llm_call(
            system_prompt="You are helpful",
            user_prompt="Hello",
            raw_response="Hi there!",
        )

        assert len(logger.llm_calls) == 1
        assert logger.llm_calls[0].system_prompt == "You are helpful"
        assert logger.llm_calls[0].user_prompt == "Hello"
        assert logger.llm_calls[0].raw_response == "Hi there!"

    def test_log_llm_call_with_tokens(self):
        """Test logging LLM call with token counts."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_llm_call(
            system_prompt="System",
            user_prompt="User",
            raw_response="Response",
            tokens_in=100,
            tokens_out=50,
        )

        assert logger.llm_calls[0].tokens_in == 100
        assert logger.llm_calls[0].tokens_out == 50
        assert logger.total_tokens_in == 100
        assert logger.total_tokens_out == 50

    def test_log_llm_call_accumulates_tokens(self):
        """Test that token counts accumulate."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_llm_call("S", "U", "R", tokens_in=100, tokens_out=50)
        logger.log_llm_call("S", "U", "R", tokens_in=200, tokens_out=100)

        assert logger.total_tokens_in == 300
        assert logger.total_tokens_out == 150

    def test_log_llm_call_with_error(self):
        """Test logging LLM call with error."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_llm_call(
            system_prompt="System",
            user_prompt="User",
            raw_response="",
            error="API Error",
            error_traceback="Traceback details...",
        )

        assert logger.llm_calls[0].error == "API Error"
        assert logger.llm_calls[0].error_traceback == "Traceback details..."


class TestExecutionLoggerLogHTTPRequest:
    """Tests for ExecutionLogger.log_http_request method."""

    def test_log_http_request_basic(self):
        """Test logging a basic HTTP request."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_http_request(
            method="GET",
            url="https://api.example.com",
        )

        assert len(logger.http_requests) == 1
        assert logger.http_requests[0].method == "GET"
        assert logger.http_requests[0].url == "https://api.example.com"

    def test_log_http_request_full(self):
        """Test logging full HTTP request."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_http_request(
            method="POST",
            url="https://api.example.com/create",
            request_headers={"Content-Type": "application/json"},
            request_body='{"name": "test"}',
            status_code=201,
            response_headers={"X-Id": "123"},
            response_body='{"id": 1}',
            latency_ms=100.0,
        )

        req = logger.http_requests[0]
        assert req.status_code == 201
        assert req.request_headers["Content-Type"] == "application/json"
        assert req.response_body == '{"id": 1}'


class TestExecutionLoggerLogWebSearch:
    """Tests for ExecutionLogger.log_web_search method."""

    def test_log_web_search_basic(self):
        """Test logging a basic web search."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_web_search(
            provider="anthropic",
            query="test query",
            raw_results="Search results...",
        )

        assert len(logger.web_searches) == 1
        assert logger.web_searches[0].query == "test query"
        assert logger.web_searches[0].raw_results == "Search results..."
        assert logger.web_searches[0].provider == "anthropic"

    def test_log_web_search_with_sources(self):
        """Test logging web search with sources."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_web_search(
            provider="openai",
            query="API docs",
            raw_results="Found docs",
            sources=[{"url": "https://docs.example.com"}],
        )

        assert len(logger.web_searches[0].sources) == 1


class TestExecutionLoggerLogToolExecution:
    """Tests for ExecutionLogger.log_tool_execution method."""

    def test_log_tool_execution_basic(self):
        """Test logging basic tool execution."""
        logger = ExecutionLogger("Test", "test", "test")

        logger.log_tool_execution(
            tool_name="get_weather",
            input_args={"city": "London"},
            output_result={"temp": 20},
        )

        assert len(logger.tool_executions) == 1
        assert logger.tool_executions[0].tool_name == "get_weather"
        assert logger.tool_executions[0].input_args["city"] == "London"


class TestExecutionLoggerToMarkdown:
    """Tests for ExecutionLogger.to_markdown method."""

    def test_to_markdown_basic(self):
        """Test basic markdown generation."""
        logger = ExecutionLogger("WeatherServer", "anthropic", "claude-3")
        logger.original_description = "Create a weather tool"

        md = logger.to_markdown()

        # The actual title is "# FULL Execution Log: WeatherServer"
        assert "WeatherServer" in md
        assert "anthropic" in md
        assert "claude-3" in md
        assert "Create a weather tool" in md

    def test_to_markdown_with_llm_calls(self):
        """Test markdown with LLM calls."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")
        logger.log_llm_call(
            system_prompt="Be helpful",
            user_prompt="Generate a tool",
            raw_response="Here is your tool...",
            tokens_in=100,
            tokens_out=50,
        )

        md = logger.to_markdown()

        assert "LLM" in md
        assert "anthropic" in md

    def test_to_markdown_with_steps(self):
        """Test markdown with steps."""
        logger = ExecutionLogger("Test", "test", "test")
        logger.log_step("init", "Starting generation")
        logger.log_step("complete", "Generation complete")

        md = logger.to_markdown()

        # The section is called "Execution Timeline"
        assert "Execution Timeline" in md or "init" in md or "Starting generation" in md

    def test_to_markdown_with_tools_generated(self):
        """Test markdown with tools generated list."""
        logger = ExecutionLogger("Test", "test", "test")
        logger.tools_generated = ["get_weather", "set_alarm", "send_email"]

        md = logger.to_markdown()

        assert "get_weather" in md
        assert "set_alarm" in md
        assert "send_email" in md


class TestExecutionLoggerToJson:
    """Tests for ExecutionLogger.to_json method."""

    def test_to_json_basic(self):
        """Test basic JSON generation."""
        logger = ExecutionLogger("Test", "anthropic", "claude-3")
        logger.original_description = "Test description"

        json_str = logger.to_json()
        data = json.loads(json_str)

        # The JSON has a nested structure with "metadata" key
        assert data["metadata"]["server_name"] == "Test"
        assert data["metadata"]["provider"] == "anthropic"
        assert data["metadata"]["model"] == "claude-3"

    def test_to_json_with_data(self):
        """Test JSON with logged data."""
        logger = ExecutionLogger("Test", "test", "test")
        logger.log_step("init", "Starting")
        logger.log_llm_call("System", "User", "Response", tokens_in=10, tokens_out=5)

        json_str = logger.to_json()
        data = json.loads(json_str)

        assert len(data["steps"]) == 1
        assert len(data["llm_calls"]) == 1
        # Token counts are in the "summary" section
        assert data["summary"]["total_tokens_in"] == 10
