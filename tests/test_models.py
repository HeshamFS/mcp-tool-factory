"""Tests for data models."""

import pytest
from tool_factory.models import ToolSpec, GeneratedServer, InputType


def test_tool_spec_creation():
    """Test ToolSpec can be created with required fields."""
    spec = ToolSpec(
        name="test_tool",
        description="A test tool",
        input_schema={
            "type": "object",
            "properties": {
                "param1": {"type": "string"}
            },
            "required": ["param1"]
        }
    )

    assert spec.name == "test_tool"
    assert spec.description == "A test tool"
    assert spec.dependencies == []


def test_tool_spec_to_dict():
    """Test ToolSpec.to_dict() method."""
    spec = ToolSpec(
        name="my_tool",
        description="Does something",
        input_schema={"type": "object", "properties": {}},
        dependencies=["requests"]
    )

    data = spec.to_dict()

    assert data["name"] == "my_tool"
    assert data["dependencies"] == ["requests"]


def test_input_type_enum():
    """Test InputType enum values."""
    assert InputType.NATURAL_LANGUAGE.value == "natural_language"
    assert InputType.OPENAPI.value == "openapi"
    assert InputType.PYTHON_FUNCTION.value == "python_function"
    assert InputType.DATABASE_SCHEMA.value == "database_schema"
