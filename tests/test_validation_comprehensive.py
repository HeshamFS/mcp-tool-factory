"""Comprehensive tests for validation module."""

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
    """Tests for ToolSpecSchema validation."""

    def test_valid_minimal_spec(self):
        """Test creating minimal valid spec."""
        spec = ToolSpecSchema(
            name="test_tool",
            description="A test tool",
        )
        assert spec.name == "test_tool"
        assert spec.description == "A test tool"
        # input_schema defaults to empty dict which gets validated to have type/properties
        assert spec.input_schema == {}

    def test_valid_full_spec(self):
        """Test creating full spec."""
        spec = ToolSpecSchema(
            name="get_weather",
            description="Get weather for a city",
            input_schema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
            },
            output_schema={"type": "object"},
            implementation_hints="Use httpx for API calls",
            dependencies=["httpx", "pydantic"],
        )
        assert spec.name == "get_weather"
        assert "city" in spec.input_schema["properties"]
        assert spec.dependencies == ["httpx", "pydantic"]

    def test_name_with_hyphen_converted(self):
        """Test that hyphens in name are converted to underscores."""
        spec = ToolSpecSchema(
            name="get-weather-data",
            description="Test",
        )
        assert spec.name == "get_weather_data"

    def test_name_with_spaces_converted(self):
        """Test that spaces in name are converted to underscores."""
        spec = ToolSpecSchema(
            name="get weather data",
            description="Test",
        )
        assert spec.name == "get_weather_data"

    def test_name_uppercased_lowered(self):
        """Test that uppercase names are lowercased."""
        spec = ToolSpecSchema(
            name="GetWeather",
            description="Test",
        )
        assert spec.name == "getweather"

    def test_name_with_special_chars_cleaned(self):
        """Test that special chars are removed from name."""
        spec = ToolSpecSchema(
            name="get@weather!data#",
            description="Test",
        )
        assert "@" not in spec.name
        assert "!" not in spec.name
        assert "#" not in spec.name

    def test_name_starting_with_number_prefixed(self):
        """Test that names starting with number get prefixed."""
        spec = ToolSpecSchema(
            name="123tool",
            description="Test",
        )
        assert spec.name.startswith("tool_")

    def test_empty_name_becomes_unnamed(self):
        """Test that empty name becomes unnamed_tool."""
        spec = ToolSpecSchema(
            name="",
            description="Test",
        )
        assert spec.name == "unnamed_tool"

    def test_numeric_name_converted(self):
        """Test that non-string name is converted."""
        spec = ToolSpecSchema(
            name=123,
            description="Test",
        )
        assert spec.name == "tool_123"

    def test_input_schema_defaults(self):
        """Test that empty input_schema gets defaults."""
        spec = ToolSpecSchema(
            name="test",
            description="Test",
            input_schema={},
        )
        assert spec.input_schema["type"] == "object"
        assert spec.input_schema["properties"] == {}

    def test_input_schema_adds_type(self):
        """Test that missing type is added."""
        spec = ToolSpecSchema(
            name="test",
            description="Test",
            input_schema={"properties": {"x": {"type": "string"}}},
        )
        assert spec.input_schema["type"] == "object"

    def test_input_schema_adds_properties(self):
        """Test that missing properties is added."""
        spec = ToolSpecSchema(
            name="test",
            description="Test",
            input_schema={"type": "object"},
        )
        assert "properties" in spec.input_schema

    def test_dependencies_cleaned(self):
        """Test that dependencies are cleaned of version specifiers."""
        spec = ToolSpecSchema(
            name="test",
            description="Test",
            dependencies=["httpx>=0.24.0", "pydantic==2.0", "requests<3.0"],
        )
        assert spec.dependencies == ["httpx", "pydantic", "requests"]

    def test_dependencies_filters_invalid(self):
        """Test that invalid dependencies are filtered."""
        spec = ToolSpecSchema(
            name="test",
            description="Test",
            dependencies=["httpx", "", "  ", "pydantic"],
        )
        assert "httpx" in spec.dependencies
        assert "pydantic" in spec.dependencies
        # Empty strings should be filtered out
        assert "" not in spec.dependencies


class TestExtractJsonFromResponse:
    """Tests for extract_json_from_response function."""

    def test_extract_from_json_code_block(self):
        """Test extracting from ```json block."""
        response = """Here's the result:
```json
{"name": "test", "value": 42}
```
That's all."""
        result = extract_json_from_response(response)
        assert '"name": "test"' in result
        assert '"value": 42' in result

    def test_extract_from_plain_code_block(self):
        """Test extracting from plain ``` block."""
        response = """Result:
```
[{"tool": "test"}]
```"""
        result = extract_json_from_response(response)
        assert "[" in result
        assert '"tool": "test"' in result

    def test_extract_array_without_codeblock(self):
        """Test extracting array without code block."""
        response = 'Here are the tools: [{"name": "tool1"}, {"name": "tool2"}] Done.'
        result = extract_json_from_response(response)
        assert result.startswith("[")
        assert result.endswith("]")

    def test_extract_object_without_codeblock(self):
        """Test extracting object without code block."""
        response = 'The config is: {"key": "value"}'
        result = extract_json_from_response(response)
        assert result.startswith("{")
        assert result.endswith("}")

    def test_plain_json_returned(self):
        """Test that plain JSON is returned as-is."""
        response = '{"simple": "json"}'
        result = extract_json_from_response(response)
        assert result == '{"simple": "json"}'


class TestValidateToolSpecs:
    """Tests for validate_tool_specs function."""

    def test_validate_valid_specs(self):
        """Test validating valid specs."""
        specs_data = [
            {"name": "tool1", "description": "First tool"},
            {"name": "tool2", "description": "Second tool"},
        ]
        validated = validate_tool_specs(specs_data)
        assert len(validated) == 2
        assert validated[0].name == "tool1"
        assert validated[1].name == "tool2"

    def test_validate_fixes_missing_name(self):
        """Test that missing name is fixed."""
        specs_data = [
            {"description": "No name tool"},
        ]
        validated = validate_tool_specs(specs_data)
        assert len(validated) == 1
        assert validated[0].name == "tool_1"

    def test_validate_fixes_missing_description(self):
        """Test that missing description is fixed."""
        specs_data = [
            {"name": "test_tool"},
        ]
        validated = validate_tool_specs(specs_data)
        assert len(validated) == 1
        assert validated[0].description == "No description provided"

    def test_validate_fixes_empty_name(self):
        """Test that empty name is fixed."""
        specs_data = [
            {"name": "", "description": "Test"},
        ]
        validated = validate_tool_specs(specs_data)
        assert len(validated) == 1
        # Empty name becomes unnamed_tool through validator
        assert validated[0].name == "unnamed_tool"

    def test_validate_multiple_with_fixes(self):
        """Test validating multiple specs with fixes."""
        specs_data = [
            {"name": "valid_tool", "description": "Valid"},
            {"description": "Missing name"},
            {"name": "another_valid", "description": "Also valid"},
        ]
        validated = validate_tool_specs(specs_data)
        assert len(validated) == 3


class TestParseLLMToolResponse:
    """Tests for parse_llm_tool_response function."""

    def test_parse_valid_array(self):
        """Test parsing valid array response."""
        response = '[{"name": "tool", "description": "A tool"}]'
        result = parse_llm_tool_response(response)
        assert len(result) == 1
        assert result[0]["name"] == "tool"

    def test_parse_with_markdown(self):
        """Test parsing response with markdown."""
        response = """```json
[{"name": "test", "description": "Test tool"}]
```"""
        result = parse_llm_tool_response(response)
        assert len(result) == 1

    def test_parse_dict_with_tools_key(self):
        """Test parsing dict with 'tools' key."""
        response = '{"tools": [{"name": "tool1", "description": "First"}]}'
        result = parse_llm_tool_response(response)
        assert len(result) == 1
        assert result[0]["name"] == "tool1"

    def test_parse_single_tool_dict(self):
        """Test parsing single tool as dict."""
        response = '{"name": "single_tool", "description": "Single"}'
        result = parse_llm_tool_response(response)
        assert len(result) == 1
        assert result[0]["name"] == "single_tool"

    def test_parse_fixes_trailing_comma(self):
        """Test parsing fixes trailing comma."""
        response = '[{"name": "tool", "description": "Test",}]'
        result = parse_llm_tool_response(response)
        assert len(result) == 1

    def test_parse_invalid_json_raises(self):
        """Test that invalid JSON raises ValueError."""
        response = "This is not valid JSON at all {{{"
        with pytest.raises(ValueError, match="Failed to parse"):
            parse_llm_tool_response(response)

    def test_parse_invalid_format_raises(self):
        """Test that unexpected format raises ValueError."""
        response = '{"unexpected": "format"}'
        with pytest.raises(ValueError, match="Unexpected response format"):
            parse_llm_tool_response(response)

    def test_parse_non_list_raises(self):
        """Test that non-list data raises ValueError."""
        response = '"just a string"'
        with pytest.raises(ValueError, match="Expected list"):
            parse_llm_tool_response(response)


class TestValidatePythonCode:
    """Tests for validate_python_code function."""

    def test_valid_code(self):
        """Test validating valid Python code."""
        code = """
def hello():
    return "Hello, World!"

class MyClass:
    pass
"""
        is_valid, error = validate_python_code(code)
        assert is_valid is True
        assert error is None

    def test_invalid_syntax(self):
        """Test detecting invalid syntax."""
        code = """
def broken(
    return "missing paren"
"""
        is_valid, error = validate_python_code(code)
        assert is_valid is False
        assert "Syntax error" in error

    def test_indentation_error(self):
        """Test detecting indentation error."""
        code = """
def test():
print("wrong indent")
"""
        is_valid, error = validate_python_code(code)
        assert is_valid is False
        assert error is not None

    def test_empty_code(self):
        """Test empty code is valid."""
        code = ""
        is_valid, error = validate_python_code(code)
        assert is_valid is True
        assert error is None

    def test_only_comments(self):
        """Test code with only comments is valid."""
        code = "# Just a comment\n# Another comment"
        is_valid, error = validate_python_code(code)
        assert is_valid is True

    def test_complex_valid_code(self):
        """Test complex but valid code."""
        code = '''
import asyncio
from typing import Optional

async def fetch_data(url: str) -> Optional[dict]:
    """Fetch data from URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None
'''
        is_valid, error = validate_python_code(code)
        assert is_valid is True
