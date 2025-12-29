"""Comprehensive tests for generators/docs module."""

import pytest
from tool_factory.generators.docs import DocsGenerator
from tool_factory.models import ToolSpec


class TestDocsGeneratorReadme:
    """Tests for README generation."""

    @pytest.fixture
    def generator(self):
        """Create a DocsGenerator instance."""
        return DocsGenerator()

    def test_generate_readme_basic(self, generator):
        """Test generating basic README."""
        spec = ToolSpec(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
        )

        readme = generator.generate_readme("TestServer", [spec])

        assert "# TestServer" in readme
        assert "test_tool" in readme
        assert "Quick Start" in readme
        assert "Installation" in readme
        assert "Testing" in readme

    def test_generate_readme_with_description(self, generator):
        """Test generating README with custom description."""
        readme = generator.generate_readme(
            "MyServer",
            [],
            description="This is a custom server description.",
        )

        assert "# MyServer" in readme
        assert "This is a custom server description." in readme

    def test_generate_readme_without_description(self, generator):
        """Test generating README uses default description."""
        readme = generator.generate_readme("DefaultServer", [])

        # New format includes MCP overview and tool count
        assert "An MCP server providing 0 tools" in readme
        assert "Model Context Protocol" in readme

    def test_generate_readme_with_auth_env_vars(self, generator):
        """Test generating README with auth environment variables."""
        readme = generator.generate_readme(
            "AuthServer",
            [],
            auth_env_vars=["API_KEY", "SECRET_TOKEN"],
        )

        assert "Environment Variables" in readme
        assert "API_KEY" in readme
        assert "SECRET_TOKEN" in readme
        assert "export API_KEY" in readme

    def test_generate_readme_with_tool_parameters(self, generator):
        """Test generating README with tool parameters."""
        spec = ToolSpec(
            name="get_weather",
            description="Get weather for a city",
            input_schema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "units": {"type": "string", "description": "Temperature units"},
                },
                "required": ["city"],
            },
        )

        readme = generator.generate_readme("WeatherServer", [spec])

        assert "get_weather" in readme
        assert "**Parameters:**" in readme
        assert "city" in readme
        assert "units" in readme
        assert "City name" in readme
        assert "Yes" in readme  # Required
        assert "No" in readme  # Optional

    def test_generate_readme_with_output_schema(self, generator):
        """Test generating README with output schema."""
        spec = ToolSpec(
            name="calculate",
            description="Calculate something",
            input_schema={"type": "object", "properties": {}},
            output_schema={
                "type": "object",
                "properties": {
                    "result": {"type": "number", "description": "The result"},
                    "error": {"type": "string", "description": "Error message if any"},
                },
            },
        )

        readme = generator.generate_readme("CalcServer", [spec])

        assert "**Returns:**" in readme
        assert "result" in readme
        assert "error" in readme

    def test_generate_readme_claude_config(self, generator):
        """Test README includes Claude configuration."""
        readme = generator.generate_readme("MyServer", [])

        assert "Claude Code" in readme or "Claude Desktop" in readme
        assert "mcpServers" in readme
        assert "command" in readme
        assert "args" in readme

    def test_generate_readme_openai_sdk(self, generator):
        """Test README includes OpenAI SDK example."""
        readme = generator.generate_readme("MyServer", [])

        assert "OpenAI Agents SDK" in readme
        assert "MCPServerStdio" in readme

    def test_generate_readme_langchain(self, generator):
        """Test README includes LangChain example."""
        readme = generator.generate_readme("MyServer", [])

        assert "LangChain" in readme
        assert "load_mcp_tools" in readme

    def test_generate_readme_docker(self, generator):
        """Test README includes Docker instructions."""
        readme = generator.generate_readme("MyServer", [])

        assert "Docker" in readme
        assert "docker build" in readme
        assert "docker run" in readme

    def test_generate_readme_docker_with_env_vars(self, generator):
        """Test Docker instructions include env vars."""
        readme = generator.generate_readme(
            "MyServer",
            [],
            auth_env_vars=["API_KEY"],
        )

        assert "-e API_KEY" in readme

    def test_generate_readme_example_params(self, generator):
        """Test README generates example with different param types."""
        spec = ToolSpec(
            name="multi_type",
            description="Tool with multiple param types",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "count": {"type": "integer"},
                    "value": {"type": "number"},
                    "enabled": {"type": "boolean"},
                    "data": {"type": "object"},
                },
            },
        )

        readme = generator.generate_readme("TypeServer", [spec])

        assert "Example" in readme
        # Only first 3 params are used in examples
        assert 'text="example"' in readme
        assert "count=1" in readme
        assert "value=1.0" in readme

    def test_generate_readme_tool_without_params(self, generator):
        """Test README for tool without parameters."""
        spec = ToolSpec(
            name="simple_tool",
            description="A simple tool with no params",
            input_schema={"type": "object", "properties": {}},
        )

        readme = generator.generate_readme("SimpleServer", [spec])

        assert "simple_tool()" in readme

    def test_generate_readme_server_slug(self, generator):
        """Test README uses proper server slug."""
        readme = generator.generate_readme("My Cool Server", [])

        assert "my-cool-server" in readme


class TestDocsGeneratorSkill:
    """Tests for skill file generation."""

    @pytest.fixture
    def generator(self):
        """Create a DocsGenerator instance."""
        return DocsGenerator()

    def test_generate_skill_basic(self, generator):
        """Test generating basic skill file."""
        spec = ToolSpec(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
        )

        skill = generator.generate_skill("TestServer", [spec])

        assert "# TestServer" in skill
        assert "test_tool" in skill
        assert "Available Tools" in skill

    def test_generate_skill_with_parameters(self, generator):
        """Test generating skill with parameters."""
        spec = ToolSpec(
            name="search",
            description="Search for items",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max results"},
                },
                "required": ["query"],
            },
        )

        skill = generator.generate_skill("SearchServer", [spec])

        assert "**Parameters:**" in skill
        assert "query" in skill
        assert "limit" in skill
        assert "(required)" in skill
        assert "(optional)" in skill

    def test_generate_skill_without_description(self, generator):
        """Test skill handles missing parameter description."""
        spec = ToolSpec(
            name="tool",
            description="Tool",
            input_schema={
                "type": "object",
                "properties": {
                    "param": {"type": "string"},  # No description
                },
            },
        )

        skill = generator.generate_skill("Server", [spec])

        assert "No description" in skill

    def test_generate_skill_example(self, generator):
        """Test skill includes example."""
        spec = ToolSpec(
            name="greet",
            description="Greet a user",
            input_schema={"type": "object", "properties": {}},
        )

        skill = generator.generate_skill("GreetServer", [spec])

        assert "**Example:**" in skill
        assert "Use the greet tool" in skill

    def test_generate_skill_setup_section(self, generator):
        """Test skill includes setup section."""
        skill = generator.generate_skill("MyServer", [])

        assert "## Setup" in skill
        assert "mcpServers" in skill
        assert "command" in skill
        assert "args" in skill

    def test_generate_skill_multiple_tools(self, generator):
        """Test skill with multiple tools."""
        specs = [
            ToolSpec("tool1", "First tool", {"type": "object", "properties": {}}),
            ToolSpec("tool2", "Second tool", {"type": "object", "properties": {}}),
            ToolSpec("tool3", "Third tool", {"type": "object", "properties": {}}),
        ]

        skill = generator.generate_skill("MultiServer", specs)

        assert "tool1" in skill
        assert "tool2" in skill
        assert "tool3" in skill
        assert "First tool" in skill
        assert "Second tool" in skill
        assert "Third tool" in skill

    def test_generate_skill_server_slug(self, generator):
        """Test skill uses proper server slug in config."""
        skill = generator.generate_skill("My Complex Server", [])

        assert "my-complex-server" in skill
