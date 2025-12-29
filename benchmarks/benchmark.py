"""Performance benchmarks for MCP Tool Factory.

This module provides benchmarks for:
- Code generation time
- Provider comparison
- Generated server performance

Run with: python -m benchmarks.benchmark
"""

import time
import statistics
from dataclasses import dataclass
from typing import Callable
from contextlib import contextmanager


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    name: str
    iterations: int
    total_time_ms: float
    mean_time_ms: float
    std_dev_ms: float
    min_time_ms: float
    max_time_ms: float

    def __str__(self) -> str:
        return (
            f"{self.name}:\n"
            f"  Iterations: {self.iterations}\n"
            f"  Mean: {self.mean_time_ms:.2f}ms\n"
            f"  Std Dev: {self.std_dev_ms:.2f}ms\n"
            f"  Min: {self.min_time_ms:.2f}ms\n"
            f"  Max: {self.max_time_ms:.2f}ms\n"
            f"  Total: {self.total_time_ms:.2f}ms"
        )


def benchmark(name: str, iterations: int = 10) -> Callable:
    """Decorator to benchmark a function.

    Args:
        name: Benchmark name
        iterations: Number of iterations to run

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> BenchmarkResult:
            times = []

            for _ in range(iterations):
                start = time.perf_counter()
                func(*args, **kwargs)
                end = time.perf_counter()
                times.append((end - start) * 1000)  # Convert to ms

            return BenchmarkResult(
                name=name,
                iterations=iterations,
                total_time_ms=sum(times),
                mean_time_ms=statistics.mean(times),
                std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
                min_time_ms=min(times),
                max_time_ms=max(times),
            )

        return wrapper

    return decorator


@contextmanager
def timer(name: str):
    """Context manager to time a block of code.

    Args:
        name: Name for the timing

    Yields:
        None
    """
    start = time.perf_counter()
    yield
    end = time.perf_counter()
    print(f"{name}: {(end - start) * 1000:.2f}ms")


class CodeGenerationBenchmarks:
    """Benchmarks for code generation."""

    @benchmark("Server Code Generation", iterations=5)
    def benchmark_server_generation(self):
        """Benchmark server code generation."""
        from tool_factory.generators.server import ServerGenerator
        from tool_factory.models import ToolSpec

        generator = ServerGenerator()

        # Create sample tool specs
        specs = [
            ToolSpec(
                name=f"tool_{i}",
                description=f"Tool number {i}",
                input_schema={
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string"},
                        "param2": {"type": "integer"},
                    },
                    "required": ["param1"],
                },
            )
            for i in range(10)
        ]

        # Create implementations for each tool
        implementations = {
            f"tool_{i}": f'return {{"status": "ok", "tool": {i}}}'
            for i in range(10)
        }

        generator.generate_server("BenchmarkServer", specs, implementations)

    @benchmark("Template Rendering", iterations=20)
    def benchmark_template_rendering(self):
        """Benchmark Jinja2 template rendering."""
        from jinja2 import Template

        template_str = """
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("{{ server_name }}")

        {% for tool in tools %}
        @mcp.tool()
        def {{ tool.name }}({% for p in tool.params %}{{ p.name }}: {{ p.type }}{% if not loop.last %}, {% endif %}{% endfor %}) -> dict:
            '''{{ tool.description }}'''
            return {"status": "ok"}
        {% endfor %}
        """

        template = Template(template_str)
        template.render(
            server_name="TestServer",
            tools=[
                {
                    "name": f"tool_{i}",
                    "description": f"Tool {i}",
                    "params": [
                        {"name": "param1", "type": "str"},
                        {"name": "param2", "type": "int"},
                    ],
                }
                for i in range(20)
            ],
        )

    @benchmark("Input Validation", iterations=100)
    def benchmark_validation(self):
        """Benchmark input validation."""
        from tool_factory.utils.input_validation import (
            validate_string,
            validate_email,
            validate_url,
            validate_integer,
        )

        validate_string("test string", "test")
        validate_email("user@example.com", "email")
        validate_url("https://example.com/path", "url")
        validate_integer(42, "number")

    @benchmark("Security Scanning", iterations=10)
    def benchmark_security_scan(self):
        """Benchmark security scanning."""
        from tool_factory.security import scan_code

        code = '''
        import os
        import subprocess

        def unsafe_function(user_input):
            password = "hardcoded123"
            result = eval(user_input)
            os.system(f"echo {user_input}")
            subprocess.run(user_input, shell=True)
            return result
        '''

        scan_code(code)

    @benchmark("OpenAPI Parsing", iterations=10)
    def benchmark_openapi_parsing(self):
        """Benchmark OpenAPI spec parsing."""
        from tool_factory.openapi import OpenAPIParser

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                f"/endpoint{i}": {
                    "get": {
                        "summary": f"Get endpoint {i}",
                        "parameters": [
                            {
                                "name": "param",
                                "in": "query",
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {"200": {"description": "Success"}},
                    },
                    "post": {
                        "summary": f"Create endpoint {i}",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    },
                }
                for i in range(20)
            },
        }

        parser = OpenAPIParser(spec)
        parser.get_endpoints()


class ProviderBenchmarks:
    """Benchmarks for LLM providers (mocked)."""

    @benchmark("Provider Initialization", iterations=20)
    def benchmark_provider_init(self):
        """Benchmark provider initialization."""
        from tool_factory.providers import (
            AnthropicProvider,
            OpenAIProvider,
            GoogleProvider,
        )

        AnthropicProvider(api_key="test", model="claude-3-opus")
        OpenAIProvider(api_key="test", model="gpt-4")
        GoogleProvider(api_key="test", model="gemini-pro")


def run_all_benchmarks():
    """Run all benchmarks and print results."""
    print("=" * 60)
    print("MCP Tool Factory Performance Benchmarks")
    print("=" * 60)
    print()

    # Code generation benchmarks
    print("Code Generation Benchmarks")
    print("-" * 40)

    cg = CodeGenerationBenchmarks()

    with timer("Warmup"):
        pass

    try:
        result = cg.benchmark_server_generation()
        print(result)
        print()
    except Exception as e:
        print(f"Server generation: Skipped ({e})")
        print()

    result = cg.benchmark_template_rendering()
    print(result)
    print()

    result = cg.benchmark_validation()
    print(result)
    print()

    result = cg.benchmark_security_scan()
    print(result)
    print()

    result = cg.benchmark_openapi_parsing()
    print(result)
    print()

    # Provider benchmarks
    print("Provider Benchmarks")
    print("-" * 40)

    pb = ProviderBenchmarks()

    result = pb.benchmark_provider_init()
    print(result)
    print()

    print("=" * 60)
    print("Benchmarks Complete")
    print("=" * 60)


if __name__ == "__main__":
    run_all_benchmarks()
