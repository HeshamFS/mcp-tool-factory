"""Full raw execution logger that captures EVERYTHING - no truncation, no summaries.

This logger captures the COMPLETE raw execution trace:
- FULL raw prompts sent to LLMs (no truncation)
- FULL raw responses received (no truncation)
- FULL HTTP request data (method, url, headers, body)
- FULL HTTP response data (status, headers, body)
- FULL web search queries and results
- FULL tool execution inputs and outputs
- All timing and metadata
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RawLLMCall:
    """Complete record of an LLM API call - FULL DATA."""

    timestamp: str
    provider: str
    model: str

    # FULL request data
    system_prompt: str  # Full system prompt
    user_prompt: str  # Full user prompt
    request_params: dict[
        str, Any
    ]  # All parameters sent (max_tokens, temperature, etc.)

    # FULL response data
    raw_response: str  # Full raw response text
    response_object: dict[str, Any] | None = (
        None  # Full API response object if available
    )

    # Token counts
    tokens_in: int | None = None
    tokens_out: int | None = None

    # Timing
    latency_ms: float = 0

    # Error if any
    error: str | None = None
    error_traceback: str | None = None


@dataclass
class RawHTTPRequest:
    """Complete record of an HTTP request - FULL DATA."""

    timestamp: str

    # FULL request data
    method: str
    url: str
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body: str = ""  # Full body

    # FULL response data
    status_code: int | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: str = ""  # FULL response body - no truncation

    # Timing
    latency_ms: float = 0

    # Error if any
    error: str | None = None


@dataclass
class RawWebSearch:
    """Complete record of a web search - FULL DATA."""

    timestamp: str
    provider: str  # anthropic, openai, google

    # Search query
    query: str

    # FULL raw search results
    raw_results: str  # Full raw results from API
    sources: list[dict[str, Any]] = field(default_factory=list)  # Full source data

    # API call details
    api_request: dict[str, Any] = field(default_factory=dict)
    api_response: dict[str, Any] = field(default_factory=dict)

    # Timing
    latency_ms: float = 0

    # Error if any
    error: str | None = None


@dataclass
class RawToolExecution:
    """Complete record of a tool execution - FULL DATA."""

    timestamp: str
    tool_name: str

    # FULL input/output
    input_args: dict[str, Any] = field(default_factory=dict)
    output_result: Any = None

    # Timing
    latency_ms: float = 0

    # Error if any
    error: str | None = None


@dataclass
class ExecutionStep:
    """A single step in the execution."""

    timestamp: str
    step_type: str
    description: str
    raw_data: dict[str, Any] = field(default_factory=dict)


class ExecutionLogger:
    """Logger that captures FULL raw execution trace data - NO TRUNCATION."""

    def __init__(self, server_name: str, provider: str, model: str):
        self.server_name = server_name
        self.provider = provider
        self.model = model
        self.start_time = datetime.now()
        self.original_description = ""
        self.web_search_enabled = False

        # FULL raw execution data - no truncation
        self.llm_calls: list[RawLLMCall] = []
        self.http_requests: list[RawHTTPRequest] = []
        self.web_searches: list[RawWebSearch] = []
        self.tool_executions: list[RawToolExecution] = []
        self.steps: list[ExecutionStep] = []

        # Summary counters
        self.tools_generated: list[str] = []
        self.total_tokens_in = 0
        self.total_tokens_out = 0

    def log_step(self, step_type: str, description: str, **raw_data: Any) -> None:
        """Log an execution step with full raw data."""
        self.steps.append(
            ExecutionStep(
                timestamp=datetime.now().isoformat(),
                step_type=step_type,
                description=description,
                raw_data=raw_data,
            )
        )

    def log_llm_call(
        self,
        system_prompt: str,
        user_prompt: str,
        raw_response: str,
        request_params: dict[str, Any] | None = None,
        response_object: dict[str, Any] | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        latency_ms: float = 0,
        error: str | None = None,
        error_traceback: str | None = None,
    ) -> None:
        """Log a FULL LLM API call with complete request/response data."""
        call = RawLLMCall(
            timestamp=datetime.now().isoformat(),
            provider=self.provider,
            model=self.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            request_params=request_params or {},
            raw_response=raw_response,
            response_object=response_object,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            error=error,
            error_traceback=error_traceback,
        )
        self.llm_calls.append(call)
        if tokens_in:
            self.total_tokens_in += tokens_in
        if tokens_out:
            self.total_tokens_out += tokens_out

    def log_http_request(
        self,
        method: str,
        url: str,
        request_headers: dict[str, str] | None = None,
        request_body: str = "",
        status_code: int | None = None,
        response_headers: dict[str, str] | None = None,
        response_body: str = "",  # FULL body
        latency_ms: float = 0,
        error: str | None = None,
    ) -> None:
        """Log a FULL HTTP request with complete headers and body."""
        request = RawHTTPRequest(
            timestamp=datetime.now().isoformat(),
            method=method,
            url=url,
            request_headers=request_headers or {},
            request_body=request_body,
            status_code=status_code,
            response_headers=response_headers or {},
            response_body=response_body,  # NO TRUNCATION
            latency_ms=latency_ms,
            error=error,
        )
        self.http_requests.append(request)

    def log_web_search(
        self,
        provider: str,
        query: str,
        raw_results: str,  # FULL results
        sources: list[dict[str, Any]] | None = None,
        api_request: dict[str, Any] | None = None,
        api_response: dict[str, Any] | None = None,
        latency_ms: float = 0,
        error: str | None = None,
    ) -> None:
        """Log a FULL web search with complete results."""
        search = RawWebSearch(
            timestamp=datetime.now().isoformat(),
            provider=provider,
            query=query,
            raw_results=raw_results,  # NO TRUNCATION
            sources=sources or [],
            api_request=api_request or {},
            api_response=api_response or {},
            latency_ms=latency_ms,
            error=error,
        )
        self.web_searches.append(search)

    def log_tool_execution(
        self,
        tool_name: str,
        input_args: dict[str, Any],
        output_result: Any = None,
        latency_ms: float = 0,
        error: str | None = None,
    ) -> None:
        """Log a tool execution with full input/output."""
        execution = RawToolExecution(
            timestamp=datetime.now().isoformat(),
            tool_name=tool_name,
            input_args=input_args,
            output_result=output_result,
            latency_ms=latency_ms,
            error=error,
        )
        self.tool_executions.append(execution)

    def to_markdown(self) -> str:
        """Generate FULL execution log as markdown - NO TRUNCATION."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        lines = [
            f"# FULL Execution Log: {self.server_name}",
            "",
            "**This log contains COMPLETE raw data - no truncation, no summaries.**",
            "",
            "## Execution Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Started | `{self.start_time.isoformat()}` |",
            f"| Finished | `{end_time.isoformat()}` |",
            f"| Duration | `{duration:.2f}s` |",
            f"| Provider | `{self.provider}` |",
            f"| Model | `{self.model}` |",
            f"| Web Search | `{self.web_search_enabled}` |",
            f"| LLM Calls | `{len(self.llm_calls)}` |",
            f"| HTTP Requests | `{len(self.http_requests)}` |",
            f"| Web Searches | `{len(self.web_searches)}` |",
            f"| Tool Executions | `{len(self.tool_executions)}` |",
            f"| Total Tokens In | `{self.total_tokens_in}` |",
            f"| Total Tokens Out | `{self.total_tokens_out}` |",
            f"| Tools Generated | `{len(self.tools_generated)}` |",
            "",
            "---",
            "",
            "## Original Request",
            "",
            "```",
            self.original_description,
            "```",
            "",
        ]

        # ==================== WEB SEARCHES (FULL) ====================
        if self.web_searches:
            lines.extend(
                [
                    "---",
                    "",
                    "## Web Searches (FULL RAW DATA)",
                    "",
                ]
            )
            for i, search in enumerate(self.web_searches, 1):
                lines.extend(
                    [
                        f"### Web Search {i}",
                        "",
                        f"- **Timestamp:** `{search.timestamp}`",
                        f"- **Provider:** `{search.provider}`",
                        f"- **Query:** `{search.query}`",
                        f"- **Latency:** `{search.latency_ms:.0f}ms`",
                    ]
                )
                if search.error:
                    lines.append(f"- **Error:** `{search.error}`")

                # Full API request
                if search.api_request:
                    lines.extend(
                        [
                            "",
                            "#### API Request (RAW):",
                            "",
                            "```json",
                            json.dumps(search.api_request, indent=2, default=str),
                            "```",
                        ]
                    )

                # Full API response
                if search.api_response:
                    lines.extend(
                        [
                            "",
                            "#### API Response (RAW):",
                            "",
                            "```json",
                            json.dumps(search.api_response, indent=2, default=str),
                            "```",
                        ]
                    )

                # Full raw results
                lines.extend(
                    [
                        "",
                        "#### Full Raw Results:",
                        "",
                        "```",
                        search.raw_results,  # NO TRUNCATION
                        "```",
                        "",
                    ]
                )

                # Full sources
                if search.sources:
                    lines.extend(
                        [
                            "#### Sources (FULL DATA):",
                            "",
                            "```json",
                            json.dumps(search.sources, indent=2, default=str),
                            "```",
                            "",
                        ]
                    )

        # ==================== HTTP REQUESTS (FULL) ====================
        if self.http_requests:
            lines.extend(
                [
                    "---",
                    "",
                    "## HTTP Requests (FULL RAW DATA)",
                    "",
                ]
            )
            for i, req in enumerate(self.http_requests, 1):
                lines.extend(
                    [
                        f"### HTTP Request {i}: {req.method} {req.url}",
                        "",
                        f"- **Timestamp:** `{req.timestamp}`",
                        f"- **Method:** `{req.method}`",
                        f"- **URL:** `{req.url}`",
                        f"- **Status Code:** `{req.status_code}`",
                        f"- **Latency:** `{req.latency_ms:.0f}ms`",
                    ]
                )
                if req.error:
                    lines.append(f"- **Error:** `{req.error}`")

                # Full request headers
                if req.request_headers:
                    lines.extend(
                        [
                            "",
                            "#### Request Headers:",
                            "",
                            "```json",
                            json.dumps(req.request_headers, indent=2),
                            "```",
                        ]
                    )

                # Full request body
                if req.request_body:
                    lines.extend(
                        [
                            "",
                            "#### Request Body (FULL):",
                            "",
                            "```",
                            req.request_body,  # NO TRUNCATION
                            "```",
                        ]
                    )

                # Full response headers
                if req.response_headers:
                    lines.extend(
                        [
                            "",
                            "#### Response Headers:",
                            "",
                            "```json",
                            json.dumps(req.response_headers, indent=2),
                            "```",
                        ]
                    )

                # Full response body
                lines.extend(
                    [
                        "",
                        "#### Response Body (FULL):",
                        "",
                        "```",
                        req.response_body,  # NO TRUNCATION
                        "```",
                        "",
                    ]
                )

        # ==================== LLM CALLS (FULL) ====================
        if self.llm_calls:
            lines.extend(
                [
                    "---",
                    "",
                    "## LLM API Calls (FULL RAW DATA)",
                    "",
                ]
            )
            for i, call in enumerate(self.llm_calls, 1):
                tokens_info = ""
                if call.tokens_in or call.tokens_out:
                    tokens_info = f" | Tokens: {call.tokens_in or '?'} in, {call.tokens_out or '?'} out"

                lines.extend(
                    [
                        f"### LLM Call {i}: {call.provider}/{call.model}",
                        "",
                        f"- **Timestamp:** `{call.timestamp}`",
                        f"- **Latency:** `{call.latency_ms:.0f}ms`{tokens_info}",
                    ]
                )
                if call.error:
                    lines.append(f"- **Error:** `{call.error}`")
                    if call.error_traceback:
                        lines.extend(
                            [
                                "",
                                "#### Error Traceback:",
                                "",
                                "```",
                                call.error_traceback,
                                "```",
                            ]
                        )

                # Full request parameters
                if call.request_params:
                    lines.extend(
                        [
                            "",
                            "#### Request Parameters:",
                            "",
                            "```json",
                            json.dumps(call.request_params, indent=2, default=str),
                            "```",
                        ]
                    )

                # FULL system prompt
                lines.extend(
                    [
                        "",
                        "#### System Prompt (FULL):",
                        "",
                        "```",
                        call.system_prompt,  # NO TRUNCATION
                        "```",
                        "",
                    ]
                )

                # FULL user prompt
                lines.extend(
                    [
                        "#### User Prompt (FULL):",
                        "",
                        "```",
                        call.user_prompt,  # NO TRUNCATION
                        "```",
                        "",
                    ]
                )

                # FULL raw response
                lines.extend(
                    [
                        "#### Raw Response (FULL):",
                        "",
                        "```",
                        call.raw_response,  # NO TRUNCATION
                        "```",
                        "",
                    ]
                )

                # Full response object if available
                if call.response_object:
                    lines.extend(
                        [
                            "#### Full Response Object:",
                            "",
                            "```json",
                            json.dumps(call.response_object, indent=2, default=str),
                            "```",
                            "",
                        ]
                    )

        # ==================== TOOL EXECUTIONS (FULL) ====================
        if self.tool_executions:
            lines.extend(
                [
                    "---",
                    "",
                    "## Tool Executions (FULL RAW DATA)",
                    "",
                ]
            )
            for i, exe in enumerate(self.tool_executions, 1):
                lines.extend(
                    [
                        f"### Tool Execution {i}: {exe.tool_name}",
                        "",
                        f"- **Timestamp:** `{exe.timestamp}`",
                        f"- **Latency:** `{exe.latency_ms:.0f}ms`",
                    ]
                )
                if exe.error:
                    lines.append(f"- **Error:** `{exe.error}`")

                # Full input
                lines.extend(
                    [
                        "",
                        "#### Input Arguments (FULL):",
                        "",
                        "```json",
                        json.dumps(exe.input_args, indent=2, default=str),
                        "```",
                        "",
                    ]
                )

                # Full output
                lines.extend(
                    [
                        "#### Output Result (FULL):",
                        "",
                        "```json",
                        (
                            json.dumps(exe.output_result, indent=2, default=str)
                            if exe.output_result
                            else "null"
                        ),
                        "```",
                        "",
                    ]
                )

        # ==================== EXECUTION STEPS ====================
        if self.steps:
            lines.extend(
                [
                    "---",
                    "",
                    "## Execution Timeline",
                    "",
                    "| Time | Type | Description |",
                    "|------|------|-------------|",
                ]
            )
            for step in self.steps:
                time_str = step.timestamp.split("T")[1][:12]
                lines.append(
                    f"| `{time_str}` | `{step.step_type}` | {step.description} |"
                )

            # Full step data
            lines.extend(["", "### Step Details (FULL DATA):", ""])
            for i, step in enumerate(self.steps, 1):
                if step.raw_data:
                    lines.extend(
                        [
                            f"#### Step {i}: {step.step_type}",
                            "",
                            "```json",
                            json.dumps(step.raw_data, indent=2, default=str),
                            "```",
                            "",
                        ]
                    )

        # ==================== TOOLS GENERATED ====================
        if self.tools_generated:
            lines.extend(
                [
                    "---",
                    "",
                    "## Tools Generated",
                    "",
                ]
            )
            for tool in self.tools_generated:
                lines.append(f"- `{tool}`")
            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Export FULL execution data as JSON - NO TRUNCATION."""
        end_time = datetime.now()

        return json.dumps(
            {
                "metadata": {
                    "server_name": self.server_name,
                    "provider": self.provider,
                    "model": self.model,
                    "start_time": self.start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": (end_time - self.start_time).total_seconds(),
                    "web_search_enabled": self.web_search_enabled,
                    "original_description": self.original_description,
                },
                "summary": {
                    "total_llm_calls": len(self.llm_calls),
                    "total_http_requests": len(self.http_requests),
                    "total_web_searches": len(self.web_searches),
                    "total_tool_executions": len(self.tool_executions),
                    "total_tokens_in": self.total_tokens_in,
                    "total_tokens_out": self.total_tokens_out,
                    "tools_generated": self.tools_generated,
                },
                "llm_calls": [
                    {
                        "timestamp": c.timestamp,
                        "provider": c.provider,
                        "model": c.model,
                        "system_prompt": c.system_prompt,  # FULL
                        "user_prompt": c.user_prompt,  # FULL
                        "request_params": c.request_params,
                        "raw_response": c.raw_response,  # FULL
                        "response_object": c.response_object,
                        "tokens_in": c.tokens_in,
                        "tokens_out": c.tokens_out,
                        "latency_ms": c.latency_ms,
                        "error": c.error,
                        "error_traceback": c.error_traceback,
                    }
                    for c in self.llm_calls
                ],
                "http_requests": [
                    {
                        "timestamp": r.timestamp,
                        "method": r.method,
                        "url": r.url,
                        "request_headers": r.request_headers,
                        "request_body": r.request_body,  # FULL
                        "status_code": r.status_code,
                        "response_headers": r.response_headers,
                        "response_body": r.response_body,  # FULL
                        "latency_ms": r.latency_ms,
                        "error": r.error,
                    }
                    for r in self.http_requests
                ],
                "web_searches": [
                    {
                        "timestamp": s.timestamp,
                        "provider": s.provider,
                        "query": s.query,
                        "raw_results": s.raw_results,  # FULL
                        "sources": s.sources,  # FULL
                        "api_request": s.api_request,
                        "api_response": s.api_response,
                        "latency_ms": s.latency_ms,
                        "error": s.error,
                    }
                    for s in self.web_searches
                ],
                "tool_executions": [
                    {
                        "timestamp": e.timestamp,
                        "tool_name": e.tool_name,
                        "input_args": e.input_args,  # FULL
                        "output_result": e.output_result,  # FULL
                        "latency_ms": e.latency_ms,
                        "error": e.error,
                    }
                    for e in self.tool_executions
                ],
                "steps": [
                    {
                        "timestamp": s.timestamp,
                        "step_type": s.step_type,
                        "description": s.description,
                        "raw_data": s.raw_data,
                    }
                    for s in self.steps
                ],
            },
            indent=2,
            default=str,
        )
