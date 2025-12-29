"""Tests for validation module."""

import pytest
from pydantic import ValidationError

from tool_factory.validation import (
    ToolSpecSchema,
    extract_json_from_response,
    validate_tool_specs,
    parse_llm_tool_response,
    validate_python_code,
)


class TestToolSpecSchema:
    """Tests for ToolSpecSchema Pydantic model."""

    def test_valid_spec(self):
        """Test validation of a valid tool spec."""
        spec = ToolSpecSchema(
            name="get_weather",
            description="Get weather for a city",
            input_schema={"type": "object", "properties": {"city": {"type": "string"}}},
        )
        assert spec.name == "get_weather"
        assert spec.description == "Get weather for a city"

    def test_name_normalization(self):
        """Test that names are normalized correctly."""
        # Uppercase converted to lowercase
        spec = ToolSpecSchema(name="GetWeather", description="Test")
        assert spec.name == "getweather"

        # Hyphens converted to underscores
        spec = ToolSpecSchema(name="get-weather", description="Test")
        assert spec.name == "get_weather"

        # Spaces converted to underscores
        spec = ToolSpecSchema(name="get weather", description="Test")
        assert spec.name == "get_weather"

        # Numbers at start get prefix
        spec = ToolSpecSchema(name="123tool", description="Test")
        assert spec.name == "tool_123tool"

    def test_input_schema_defaults(self):
        """Test that input_schema gets defaults if empty."""
        spec = ToolSpecSchema(
            name="test_tool",
            description="Test",
            input_schema={},
        )
        assert spec.input_schema == {"type": "object", "properties": {}}

    def test_empty_name_auto_fixes(self):
        """Test that empty name is auto-fixed to unnamed_tool."""
        spec = ToolSpecSchema(name="", description="Test")
        assert spec.name == "unnamed_tool"

    def test_empty_description_raises(self):
        """Test that empty description raises validation error."""
        with pytest.raises(ValidationError):
            ToolSpecSchema(name="test", description="")


class TestExtractJsonFromResponse:
    """Tests for JSON extraction from LLM responses."""

    def test_json_in_code_block(self):
        """Test extraction from markdown code block."""
        response = """Here are the tools:
```json
[{"name": "test", "description": "A test"}]
```
"""
        result = extract_json_from_response(response)
        assert "[" in result
        assert '"name"' in result

    def test_plain_json(self):
        """Test extraction of plain JSON."""
        response = '[{"name": "test", "description": "A test"}]'
        result = extract_json_from_response(response)
        assert result == response

    def test_json_with_surrounding_text(self):
        """Test extraction when JSON has surrounding text."""
        response = 'Here is the result: [{"name": "test"}] hope that helps!'
        result = extract_json_from_response(response)
        assert result == '[{"name": "test"}]'


class TestParseToolResponse:
    """Tests for parsing tool responses."""

    def test_parse_valid_array(self):
        """Test parsing a valid array response."""
        response = '[{"name": "test", "description": "A test"}]'
        result = parse_llm_tool_response(response)
        assert len(result) == 1
        assert result[0]["name"] == "test"

    def test_parse_wrapped_in_key(self):
        """Test parsing when array is wrapped in a key."""
        response = '{"tools": [{"name": "test", "description": "A test"}]}'
        result = parse_llm_tool_response(response)
        assert len(result) == 1
        assert result[0]["name"] == "test"

    def test_parse_single_tool(self):
        """Test parsing a single tool object."""
        response = '{"name": "test", "description": "A test"}'
        result = parse_llm_tool_response(response)
        assert len(result) == 1

    def test_parse_with_trailing_comma(self):
        """Test parsing JSON with trailing commas (common LLM error)."""
        response = '[{"name": "test", "description": "A test",}]'
        result = parse_llm_tool_response(response)
        assert len(result) == 1

    def test_invalid_json_raises(self):
        """Test that invalid JSON raises ValueError."""
        response = "not json at all"
        with pytest.raises(ValueError):
            parse_llm_tool_response(response)


class TestValidateToolSpecs:
    """Tests for tool spec validation."""

    def test_validate_valid_specs(self):
        """Test validation of valid specs."""
        specs = [
            {"name": "tool1", "description": "First tool"},
            {"name": "tool2", "description": "Second tool"},
        ]
        result = validate_tool_specs(specs)
        assert len(result) == 2
        assert result[0].name == "tool1"
        assert result[1].name == "tool2"

    def test_auto_fix_missing_name(self):
        """Test that missing name is auto-fixed."""
        specs = [{"description": "A tool without a name"}]
        result = validate_tool_specs(specs)
        assert len(result) == 1
        assert result[0].name == "tool_1"

    def test_auto_fix_missing_description(self):
        """Test that missing description is auto-fixed."""
        specs = [{"name": "test"}]
        result = validate_tool_specs(specs)
        assert len(result) == 1
        assert result[0].description == "No description provided"


class TestValidatePythonCode:
    """Tests for Python code validation."""

    def test_valid_code(self):
        """Test validation of valid Python code."""
        code = """
def hello():
    return "world"
"""
        is_valid, error = validate_python_code(code)
        assert is_valid
        assert error is None

    def test_invalid_code(self):
        """Test validation of invalid Python code."""
        code = """
def hello(:
    return "world"
"""
        is_valid, error = validate_python_code(code)
        assert not is_valid
        assert "Syntax error" in error
