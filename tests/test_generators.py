"""Tests for code generators."""

import pytest

from tool_factory.generators.docs import DocsGenerator
from tool_factory.generators.server import ServerGenerator
from tool_factory.models import ToolSpec


@pytest.fixture
def sample_spec():
    """Create a sample tool specification."""
    return ToolSpec(
        name="get_weather",
        description="Get current weather for a city.",
        input_schema={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"},
                "unit": {
                    "type": "string",
                    "description": "Temperature unit",
                    "default": "celsius",
                },
            },
            "required": ["city"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "temperature": {"type": "number"},
                "conditions": {"type": "string"},
            },
        },
        dependencies=["requests"],
    )


class TestServerGenerator:
    """Tests for ServerGenerator."""

    def test_generate_server_simple(self, sample_spec):
        """Test simple server generation."""
        generator = ServerGenerator()

        code = generator.generate_server_simple(
            server_name="WeatherServer",
            tool_specs=[sample_spec],
            implementations={
                "get_weather": '''def get_weather(city: str, unit: str = "celsius") -> dict:
    """Get weather for a city."""
    return {"temperature": 22, "conditions": "sunny"}'''
            },
        )

        assert "FastMCP" in code
        assert "WeatherServer" in code
        assert "@mcp.tool()" in code
        assert "get_weather" in code

    def test_generate_tests(self, sample_spec):
        """Test test code generation."""
        generator = ServerGenerator()

        code = generator.generate_tests([sample_spec])

        assert "pytest" in code
        assert "test_list_tools" in code
        assert "get_weather" in code

    def test_generate_dockerfile(self, sample_spec):
        """Test Dockerfile generation."""
        generator = ServerGenerator()

        dockerfile = generator.generate_dockerfile([sample_spec])

        assert "FROM python" in dockerfile
        assert "mcp" in dockerfile
        assert "requests" in dockerfile

    def test_generate_dockerfile_with_production_deps(self, sample_spec):
        """Test Dockerfile includes production dependencies."""
        from tool_factory.production import ProductionConfig

        generator = ServerGenerator()

        config = ProductionConfig(
            enable_metrics=True,
            enable_retries=True,
        )

        dockerfile = generator.generate_dockerfile(
            [sample_spec],
            auth_env_vars=[],
            production_config=config,
        )

        assert "prometheus_client" in dockerfile
        assert "tenacity" in dockerfile

    def test_generate_dockerfile_health_check(self, sample_spec):
        """Test Dockerfile has proper health check."""
        generator = ServerGenerator()

        dockerfile = generator.generate_dockerfile([sample_spec])

        # Should import server module, not just exit(0)
        assert "import server" in dockerfile

    def test_generate_pyproject(self, sample_spec):
        """Test pyproject.toml generation."""
        generator = ServerGenerator()

        pyproject = generator.generate_pyproject("TestServer", [sample_spec])

        assert "[project]" in pyproject
        assert "testserver" in pyproject  # Name is lowercased
        assert "mcp>=1.0.0" in pyproject

    def test_extract_imports_from_implementation(self, sample_spec):
        """Test that imports are extracted from implementation code."""
        generator = ServerGenerator()

        impl_with_imports = '''import random
from datetime import datetime

def roll_dice(sides: int = 6) -> dict:
    """Roll a dice."""
    return {"result": random.randint(1, sides)}'''

        imports, cleaned = generator._extract_imports_from_implementation(
            impl_with_imports
        )

        assert len(imports) == 2
        assert "import random" in imports
        assert "from datetime import datetime" in imports
        assert "def roll_dice" in cleaned
        assert "import random" not in cleaned

    def test_generated_server_has_valid_syntax(self, sample_spec):
        """Test that generated server code compiles correctly."""
        generator = ServerGenerator()

        # Implementation that includes an import statement (common LLM output)
        impl_with_import = '''import random

def get_weather(city: str, unit: str = "celsius") -> dict:
    """Get weather for a city."""
    temp = random.randint(15, 30)
    return {"temperature": temp, "conditions": "sunny"}'''

        code = generator.generate_server_simple(
            server_name="WeatherServer",
            tool_specs=[sample_spec],
            implementations={"get_weather": impl_with_import},
        )

        # Should compile without syntax errors
        compile(code, "<string>", "exec")

        # Import should be at the top, before FastMCP instantiation
        lines = code.split("\n")
        import_line = None
        fastmcp_line = None
        decorator_line = None

        for i, line in enumerate(lines):
            if "import random" in line and import_line is None:
                import_line = i
            if "FastMCP(" in line and fastmcp_line is None:
                fastmcp_line = i
            if "@mcp.tool()" in line and decorator_line is None:
                decorator_line = i

        assert import_line is not None, "import random not found"
        assert fastmcp_line is not None, "FastMCP not found"
        assert decorator_line is not None, "@mcp.tool() not found"
        assert import_line < fastmcp_line, "import should be before FastMCP"
        assert import_line < decorator_line, "import should be before decorator"

    def test_syntax_validation(self):
        """Test syntax validation helper."""
        generator = ServerGenerator()

        # Valid code
        assert generator._validate_generated_code("x = 1\ny = 2")

        # Invalid code
        assert not generator._validate_generated_code("def foo(:\n  pass")

    def test_generate_server_with_template(self, sample_spec):
        """Test template-based server generation."""
        generator = ServerGenerator()

        impl = '''def get_weather(city: str, unit: str = "celsius") -> dict:
    """Get weather for a city."""
    return {"temperature": 22, "conditions": "sunny"}'''

        code = generator.generate_server(
            server_name="WeatherServer",
            tool_specs=[sample_spec],
            implementations={"get_weather": impl},
            auth_env_vars=["API_KEY"],
            include_health_check=True,
        )

        # Verify template rendering
        assert "FastMCP" in code
        assert "WeatherServer" in code
        assert "@mcp.tool()" in code
        assert "get_weather" in code
        assert "health_check" in code
        assert "API_KEY" in code

        # Should compile
        compile(code, "<string>", "exec")

    def test_generate_server_with_production_config(self, sample_spec):
        """Test template-based server generation with production config."""
        from tool_factory.production import ProductionConfig

        generator = ServerGenerator()

        impl = """def get_weather(city: str) -> dict:
    return {"temp": 20}"""

        config = ProductionConfig(
            enable_logging=True,
            enable_metrics=True,
        )

        code = generator.generate_server(
            server_name="ProdServer",
            tool_specs=[sample_spec],
            implementations={"get_weather": impl},
            production_config=config,
        )

        assert "STRUCTURED LOGGING" in code
        assert "PROMETHEUS METRICS" in code
        compile(code, "<string>", "exec")


class TestDocsGenerator:
    """Tests for DocsGenerator."""

    def test_generate_readme(self, sample_spec):
        """Test README generation."""
        generator = DocsGenerator()

        readme = generator.generate_readme("WeatherTools", [sample_spec])

        assert "# WeatherTools" in readme
        assert "get_weather" in readme
        assert "Claude Code" in readme
        assert "OpenAI Agents SDK" in readme

    def test_generate_skill(self, sample_spec):
        """Test skill file generation."""
        generator = DocsGenerator()

        skill = generator.generate_skill("WeatherTools", [sample_spec])

        assert "# WeatherTools" in skill
        assert "get_weather" in skill
        assert "Parameters:" in skill
        assert "mcpServers" in skill
