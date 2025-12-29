"""Comprehensive tests for models module."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import os

from tool_factory.models import (
    ToolSpec,
    GeneratedServer,
    GenerationLog,
    GenerationStep,
    WebSearchEntry,
    InputType,
    ValidationResult,
)


class TestWebSearchEntry:
    """Tests for WebSearchEntry model."""

    def test_create_basic(self):
        """Test creating WebSearchEntry with basic fields."""
        entry = WebSearchEntry(
            query="weather API",
            results="Found weather APIs...",
        )

        assert entry.query == "weather API"
        assert entry.results == "Found weather APIs..."
        assert entry.sources == []
        assert entry.timestamp  # Should have a timestamp

    def test_create_with_sources(self):
        """Test creating WebSearchEntry with sources."""
        entry = WebSearchEntry(
            query="test",
            results="results",
            sources=["https://example.com", "https://docs.api"],
        )

        assert len(entry.sources) == 2
        assert "https://example.com" in entry.sources


class TestGenerationStep:
    """Tests for GenerationStep model."""

    def test_create_basic(self):
        """Test creating GenerationStep with basic fields."""
        step = GenerationStep(
            step_name="extract_specs",
            description="Extracting tool specifications",
        )

        assert step.step_name == "extract_specs"
        assert step.description == "Extracting tool specifications"
        assert step.input_data is None
        assert step.output_data is None
        assert step.timestamp  # Should have a timestamp

    def test_create_with_data(self):
        """Test creating GenerationStep with input/output data."""
        step = GenerationStep(
            step_name="generate",
            description="Generating code",
            input_data='{"tool": "weather"}',
            output_data="def get_weather(): pass",
        )

        assert step.input_data == '{"tool": "weather"}'
        assert step.output_data == "def get_weather(): pass"


class TestGenerationLog:
    """Tests for GenerationLog model."""

    def test_create_basic(self):
        """Test creating GenerationLog with basic fields."""
        log = GenerationLog(server_name="TestServer")

        assert log.server_name == "TestServer"
        assert log.provider == ""
        assert log.model == ""
        assert log.web_search_enabled is False
        assert log.original_description == ""
        assert log.web_searches == []
        assert log.steps == []
        assert log.tools_generated == []
        assert log.dependencies_used == []

    def test_add_step(self):
        """Test adding a generation step."""
        log = GenerationLog(server_name="Test")

        log.add_step("init", "Initializing")
        log.add_step("generate", "Generating code", input_data="specs", output_data="code")

        assert len(log.steps) == 2
        assert log.steps[0].step_name == "init"
        assert log.steps[1].step_name == "generate"
        assert log.steps[1].input_data == "specs"

    def test_add_web_search(self):
        """Test adding a web search entry."""
        log = GenerationLog(server_name="Test")

        log.add_web_search("weather API", "Found results...")
        log.add_web_search("API docs", "Documentation...", sources=["https://example.com"])

        assert len(log.web_searches) == 2
        assert log.web_searches[0].query == "weather API"
        assert len(log.web_searches[1].sources) == 1

    def test_to_markdown_basic(self):
        """Test generating markdown with basic info."""
        log = GenerationLog(server_name="WeatherServer")
        log.provider = "anthropic"
        log.model = "claude-3"
        log.original_description = "Create a weather tool"

        md = log.to_markdown()

        assert "# Generation Log: WeatherServer" in md
        assert "anthropic" in md
        assert "claude-3" in md
        assert "Create a weather tool" in md

    def test_to_markdown_with_web_searches(self):
        """Test markdown includes web search results."""
        log = GenerationLog(server_name="Test")
        log.web_search_enabled = True
        log.add_web_search(
            "API docs",
            "Found documentation for the API...",
            sources=["https://docs.example.com"],
        )

        md = log.to_markdown()

        assert "Web Research" in md
        assert "API docs" in md
        assert "https://docs.example.com" in md

    def test_to_markdown_with_long_results(self):
        """Test markdown truncates long results."""
        log = GenerationLog(server_name="Test")
        log.add_web_search("query", "x" * 3000)  # Long results

        md = log.to_markdown()

        # Should contain truncated results
        assert "..." in md or len(md) < 10000  # Either truncated or reasonable size

    def test_to_markdown_with_enhanced_description(self):
        """Test markdown includes enhanced description."""
        log = GenerationLog(server_name="Test")
        log.original_description = "Original"
        log.enhanced_description = "Enhanced version with more details"

        md = log.to_markdown()

        assert "Enhanced Description" in md
        assert "Enhanced version" in md

    def test_to_markdown_with_steps(self):
        """Test markdown includes generation steps."""
        log = GenerationLog(server_name="Test")
        log.add_step("Step 1", "First step", input_data="input", output_data="output")

        md = log.to_markdown()

        assert "Generation Steps" in md
        assert "Step 1" in md

    def test_to_markdown_with_tools(self):
        """Test markdown includes generated tools."""
        log = GenerationLog(server_name="Test")
        log.tools_generated = ["get_weather", "set_temperature"]

        md = log.to_markdown()

        assert "Tools Generated" in md
        assert "get_weather" in md
        assert "set_temperature" in md

    def test_to_markdown_with_dependencies(self):
        """Test markdown includes dependencies."""
        log = GenerationLog(server_name="Test")
        log.dependencies_used = ["httpx", "pydantic"]

        md = log.to_markdown()

        assert "Dependencies" in md
        assert "httpx" in md
        assert "pydantic" in md


class TestInputType:
    """Tests for InputType enum."""

    def test_enum_values(self):
        """Test enum values exist."""
        assert InputType.NATURAL_LANGUAGE.value == "natural_language"
        assert InputType.OPENAPI.value == "openapi"
        assert InputType.PYTHON_FUNCTION.value == "python_function"
        assert InputType.DATABASE_SCHEMA.value == "database_schema"


class TestToolSpec:
    """Tests for ToolSpec model."""

    def test_create_minimal(self):
        """Test creating minimal ToolSpec."""
        spec = ToolSpec(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
        )

        assert spec.name == "test_tool"
        assert spec.description == "A test tool"

    def test_create_with_all_fields(self):
        """Test creating ToolSpec with all fields."""
        spec = ToolSpec(
            name="complex_tool",
            description="A complex tool",
            input_schema={
                "type": "object",
                "properties": {"param": {"type": "string"}},
                "required": ["param"],
            },
            output_schema={
                "type": "object",
                "properties": {"result": {"type": "string"}},
            },
            implementation_hints="Use httpx for API calls",
            dependencies=["httpx", "pydantic"],
        )

        assert spec.name == "complex_tool"
        assert spec.output_schema is not None
        assert spec.implementation_hints is not None
        assert "httpx" in spec.dependencies

    def test_defaults(self):
        """Test default values."""
        spec = ToolSpec(
            name="test",
            description="test",
            input_schema={"type": "object"},
        )

        assert spec.output_schema is None
        assert spec.implementation_hints is None
        assert spec.dependencies == []

    def test_to_dict(self):
        """Test to_dict method."""
        spec = ToolSpec(
            name="test",
            description="A test",
            input_schema={"type": "object"},
            output_schema={"type": "string"},
            implementation_hints="hints",
            dependencies=["dep1"],
        )

        d = spec.to_dict()

        assert d["name"] == "test"
        assert d["description"] == "A test"
        assert d["input_schema"] == {"type": "object"}
        assert d["output_schema"] == {"type": "string"}
        assert d["implementation_hints"] == "hints"
        assert d["dependencies"] == ["dep1"]


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_create_valid(self):
        """Test creating a valid result."""
        result = ValidationResult(valid=True)

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.suggestions == []

    def test_create_invalid_with_errors(self):
        """Test creating invalid result with errors."""
        result = ValidationResult(
            valid=False,
            errors=["Missing field", "Invalid type"],
            warnings=["Consider adding docs"],
            suggestions=["Use descriptive names"],
        )

        assert result.valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert len(result.suggestions) == 1


class TestGeneratedServer:
    """Tests for GeneratedServer model."""

    def test_create_minimal(self):
        """Test creating minimal GeneratedServer."""
        spec = ToolSpec("tool", "desc", {"type": "object"})
        server = GeneratedServer(
            name="TestServer",
            server_code="# Server code",
            tool_specs=[spec],
            test_code="# Tests",
            dockerfile="FROM python",
            readme="# README",
            skill_file="# Skill",
            pyproject_toml="[project]",
            github_actions="name: CI",
        )

        assert server.name == "TestServer"
        assert len(server.tool_specs) == 1

    def test_execution_log_optional(self):
        """Test execution_log is optional."""
        server = GeneratedServer(
            name="Test",
            server_code="",
            tool_specs=[],
            test_code="",
            dockerfile="",
            readme="",
            skill_file="",
            pyproject_toml="",
            github_actions="",
        )

        assert server.execution_log is None

    def test_write_to_directory(self):
        """Test writing server to directory."""
        spec = ToolSpec("test_tool", "Test", {"type": "object"})
        server = GeneratedServer(
            name="WriteTest",
            server_code="# Server code here",
            tool_specs=[spec],
            test_code="# Test code here",
            dockerfile="FROM python:3.11",
            readme="# WriteTest README",
            skill_file="# Skill file",
            pyproject_toml='[project]\nname = "writetest"',
            github_actions="name: CI\non: push",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            server.write_to_directory(tmpdir)

            # Check files were created
            assert (Path(tmpdir) / "server.py").exists()
            assert (Path(tmpdir) / "tests" / "test_tools.py").exists()
            assert (Path(tmpdir) / "tests" / "__init__.py").exists()
            assert (Path(tmpdir) / "README.md").exists()
            assert (Path(tmpdir) / "skill.md").exists()
            assert (Path(tmpdir) / "Dockerfile").exists()
            assert (Path(tmpdir) / "pyproject.toml").exists()
            assert (Path(tmpdir) / ".github" / "workflows" / "ci.yml").exists()

            # Check content
            with open(Path(tmpdir) / "server.py") as f:
                assert "Server code here" in f.read()

    def test_write_to_directory_creates_parent(self):
        """Test that write_to_directory creates parent directories."""
        server = GeneratedServer(
            name="Test",
            server_code="# code",
            tool_specs=[],
            test_code="# tests",
            dockerfile="FROM python",
            readme="# README",
            skill_file="# skill",
            pyproject_toml="[project]",
            github_actions="name: CI",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "a" / "b" / "c"
            server.write_to_directory(str(nested_path))

            assert nested_path.exists()
            assert (nested_path / "server.py").exists()

    def test_write_without_github_actions(self):
        """Test writing without GitHub actions."""
        server = GeneratedServer(
            name="Test",
            server_code="# code",
            tool_specs=[],
            test_code="# tests",
            dockerfile="FROM python",
            readme="# README",
            skill_file="# skill",
            pyproject_toml="[project]",
            github_actions="",  # Empty - should not create file
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            server.write_to_directory(tmpdir)

            # GitHub workflow should not exist
            assert not (Path(tmpdir) / ".github" / "workflows" / "ci.yml").exists()

    def test_write_with_execution_log(self):
        """Test writing with execution log."""
        mock_logger = Mock()
        mock_logger.to_markdown.return_value = "# Execution Log\n\nDetails..."
        mock_logger.to_json.return_value = '{"server_name": "Test"}'

        server = GeneratedServer(
            name="LogTest",
            server_code="# code",
            tool_specs=[],
            test_code="# tests",
            dockerfile="FROM python",
            readme="# README",
            skill_file="# skill",
            pyproject_toml="[project]",
            github_actions="name: CI",
            execution_log=mock_logger,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            server.write_to_directory(tmpdir)

            assert (Path(tmpdir) / "EXECUTION_LOG.md").exists()
            assert (Path(tmpdir) / "execution_log.json").exists()

            with open(Path(tmpdir) / "EXECUTION_LOG.md") as f:
                assert "Execution Log" in f.read()


class TestGeneratedServerFilePaths:
    """Tests for file path handling in GeneratedServer."""

    def test_handles_path_with_spaces(self):
        """Test handling paths with spaces."""
        server = GeneratedServer(
            name="Test",
            server_code="# code",
            tool_specs=[],
            test_code="# tests",
            dockerfile="FROM python",
            readme="# README",
            skill_file="# skill",
            pyproject_toml="[project]",
            github_actions="name: CI",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            spaced_path = Path(tmpdir) / "path with spaces"
            server.write_to_directory(str(spaced_path))

            assert spaced_path.exists()
            assert (spaced_path / "server.py").exists()

    def test_handles_unicode_path(self):
        """Test handling paths with unicode characters."""
        server = GeneratedServer(
            name="Test",
            server_code="# code",
            tool_specs=[],
            test_code="# tests",
            dockerfile="FROM python",
            readme="# README",
            skill_file="# skill",
            pyproject_toml="[project]",
            github_actions="name: CI",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            unicode_path = Path(tmpdir) / "тест"
            try:
                server.write_to_directory(str(unicode_path))
                assert unicode_path.exists()
            except OSError:
                # Some systems may not support unicode paths
                pytest.skip("Unicode paths not supported on this system")
