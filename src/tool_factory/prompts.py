"""LLM prompts for the MCP Tool Factory."""

# fmt: off
# ruff: noqa: E501
EXTRACT_TOOLS_PROMPT = """You are a tool specification extractor. Analyze the user's description and identify distinct tools needed.

For each tool, determine:
1. A clear, descriptive name in snake_case
2. A concise description of what it does (one sentence)
3. All required and optional parameters with types
4. The expected return type and structure
5. Any external APIs or libraries needed

User Description:
{description}

Return a JSON array where each element has this exact structure:
{{
  "name": "tool_name_in_snake_case",
  "description": "What the tool does in one clear sentence.",
  "input_schema": {{
    "type": "object",
    "properties": {{
      "param1": {{"type": "string", "description": "Description of param1"}},
      "param2": {{"type": "integer", "description": "Description of param2", "default": 10}}
    }},
    "required": ["param1"]
  }},
  "output_schema": {{
    "type": "object",
    "properties": {{
      "result": {{"type": "string", "description": "The result"}}
    }}
  }},
  "implementation_hints": "Use library X to fetch data from Y...",
  "dependencies": ["requests", "pandas"]
}}

Important:
- Use snake_case for tool names
- Every tool must have input_schema with "type": "object" and "properties"
- Be specific about parameter types (string, integer, number, boolean, array, object)
- Include default values where sensible
- List only the Python packages needed (not standard library)

Return ONLY the JSON array, no other text."""


GENERATE_IMPLEMENTATION_PROMPT = """Generate a production-ready Python function for this MCP tool.

Tool Specification:
- Name: {name}
- Description: {description}
- Input Schema: {input_schema}
- Output Schema: {output_schema}
- Implementation Hints: {hints}
- Dependencies: {dependencies}

Requirements:
1. Use Python 3.11+ type hints for all parameters and return type
2. Include a comprehensive docstring with Args and Returns sections
3. Handle ALL errors gracefully - return {{"error": "message"}} dict, NEVER raise exceptions
4. Validate inputs before processing
5. Use async def if the operation involves I/O (API calls, file operations)
6. Return a dictionary that matches the output schema

Example format:
```python
def tool_name(param1: str, param2: int = 10) -> dict:
    \"\"\"
    Brief description of what the tool does.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Dictionary with result fields
    \"\"\"
    try:
        # Implementation here
        return {{"result": value}}
    except Exception as e:
        return {{"error": str(e)}}
```

Return ONLY the Python function code, no markdown fences or explanations."""


GENERATE_TESTS_PROMPT = """Generate pytest tests for this MCP tool.

Tool Specification:
- Name: {name}
- Description: {description}
- Input Schema: {input_schema}
- Output Schema: {output_schema}

Generate tests covering:
1. Happy path with valid inputs
2. Edge cases (empty strings, zero values, boundary conditions)
3. Invalid inputs (wrong types, missing required fields)
4. Error handling verification

Use this testing pattern with MCP client:
```python
import pytest
import json

@pytest.mark.asyncio
async def test_{name}_valid_input(mcp_client):
    \"\"\"Test {name} with valid input.\"\"\"
    result = await mcp_client.call_tool(
        "{name}",
        {{"param1": "value"}}
    )
    data = json.loads(result.content[0].text)
    assert "error" not in data
    # Add specific assertions

@pytest.mark.asyncio
async def test_{name}_invalid_input(mcp_client):
    \"\"\"Test {name} handles invalid input gracefully.\"\"\"
    result = await mcp_client.call_tool(
        "{name}",
        {{}}  # Missing required params
    )
    # Should not crash, may return error
    assert result is not None
```

Return ONLY the Python test code, no markdown fences or explanations."""


SYSTEM_PROMPT = """You are an expert Python developer specializing in building MCP (Model Context Protocol) servers.

Your code follows these principles:
1. Type safety - Always use type hints
2. Error resilience - Never let exceptions bubble up, return error dicts
3. Clear documentation - Docstrings with Args and Returns
4. Production ready - Handle edge cases, validate inputs
5. Clean code - PEP 8 compliant, readable, maintainable

When generating tool implementations:
- Use modern Python (3.11+) features
- Prefer built-in types over typing module where possible
- Use descriptive variable names
- Keep functions focused and single-purpose
- Add comments only where logic is non-obvious"""
# fmt: on
