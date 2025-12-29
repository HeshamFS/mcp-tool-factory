"""Validation utilities for MCP Tool Factory.

This module provides Pydantic models and validation functions for
LLM responses and generated code.
"""

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)


class ToolSpecSchema(BaseModel):
    """Pydantic model for validating tool specifications from LLM responses."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] | None = None
    implementation_hints: str | None = None
    dependencies: list[str] = Field(default_factory=list)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is a valid Python identifier."""
        if not isinstance(v, str):
            v = str(v)
        # Convert to lowercase and replace spaces/hyphens with underscores
        v = v.lower().replace("-", "_").replace(" ", "_")
        # Remove non-alphanumeric characters except underscores
        v = re.sub(r"[^a-z0-9_]", "", v)
        # Ensure starts with a letter
        if v and not v[0].isalpha():
            v = "tool_" + v
        return v or "unnamed_tool"

    @field_validator("input_schema")
    @classmethod
    def validate_input_schema(cls, v: dict) -> dict:
        """Ensure input_schema has required fields."""
        if not v:
            return {"type": "object", "properties": {}}
        if "type" not in v:
            v["type"] = "object"
        if "properties" not in v:
            v["properties"] = {}
        return v

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies(cls, v: list) -> list:
        """Clean up dependency names."""
        cleaned = []
        for dep in v:
            if isinstance(dep, str):
                # Remove version specifiers for validation
                dep_name = dep.split(">=")[0].split("==")[0].split("<")[0].strip()
                if dep_name:
                    cleaned.append(dep_name)
        return cleaned


def extract_json_from_response(response: str) -> str:
    """Extract JSON content from an LLM response that may contain markdown.

    Args:
        response: Raw LLM response that may contain markdown code blocks

    Returns:
        Extracted JSON string
    """
    # Try to extract from markdown code blocks
    if "```json" in response:
        parts = response.split("```json")
        if len(parts) > 1:
            json_part = parts[1].split("```")[0]
            return json_part.strip()
    elif "```" in response:
        parts = response.split("```")
        if len(parts) > 1:
            json_part = parts[1].split("```")[0]
            return json_part.strip()

    # Try to find JSON array or object
    # Look for array first (tool specs are typically an array)
    array_match = re.search(r"\[[\s\S]*\]", response)
    if array_match:
        return array_match.group()

    # Look for object
    object_match = re.search(r"\{[\s\S]*\}", response)
    if object_match:
        return object_match.group()

    return response.strip()


def validate_tool_specs(specs_data: list[dict]) -> list[ToolSpecSchema]:
    """Validate a list of tool specifications.

    Args:
        specs_data: List of dictionaries containing tool specs

    Returns:
        List of validated ToolSpecSchema objects

    Raises:
        ValidationError: If validation fails for any spec
    """
    validated = []
    for i, spec in enumerate(specs_data):
        try:
            validated_spec = ToolSpecSchema.model_validate(spec)
            validated.append(validated_spec)
        except ValidationError as e:
            logger.warning(f"Tool spec {i} validation failed: {e}")
            # Try to fix common issues
            if "name" not in spec or not spec["name"]:
                spec["name"] = f"tool_{i + 1}"
            if "description" not in spec or not spec["description"]:
                spec["description"] = "No description provided"
            try:
                validated_spec = ToolSpecSchema.model_validate(spec)
                validated.append(validated_spec)
            except ValidationError:
                raise

    return validated


def parse_llm_tool_response(response: str, max_retries: int = 0) -> list[dict]:
    """Parse LLM response containing tool specifications.

    Args:
        response: Raw LLM response
        max_retries: Number of times to retry with relaxed parsing (not used here)

    Returns:
        List of tool spec dictionaries

    Raises:
        ValueError: If parsing fails completely
    """
    # Extract JSON from response
    json_str = extract_json_from_response(response)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        # Try to fix common JSON issues
        # Remove trailing commas
        fixed = re.sub(r",(\s*[}\]])", r"\1", json_str)
        # Try again
        try:
            data = json.loads(fixed)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON: {e}")
            raise ValueError(
                f"Failed to parse tool specifications: {e}\nResponse: {response[:500]}..."
            )

    # Ensure we have a list
    if isinstance(data, dict):
        # Maybe it's a single tool spec or wrapped in a key
        if "tools" in data:
            data = data["tools"]
        elif "name" in data:
            data = [data]
        else:
            raise ValueError(f"Unexpected response format: {type(data)}")

    if not isinstance(data, list):
        raise ValueError(f"Expected list of tool specs, got: {type(data)}")

    return data


def validate_python_code(code: str) -> tuple[bool, str | None]:
    """Validate that Python code compiles correctly.

    Args:
        code: Python source code to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        compile(code, "<generated>", "exec")
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
