"""Comprehensive tests for generators/server.py module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from tool_factory.generators.server import ServerGenerator
from tool_factory.models import ToolSpec
from tool_factory.production import ProductionConfig


class TestServerGeneratorInit:
    """Tests for ServerGenerator initialization."""

    def test_init_creates_jinja_env(self):
        """Test that init creates Jinja2 environment."""
        gen = ServerGenerator()
        assert gen.env is not None

    def test_init_env_has_templates(self):
        """Test that environment can load templates."""
        gen = ServerGenerator()
        # Should not raise
        template = gen.env.get_template("server.py.jinja")
        assert template is not None


class TestGenerateServer:
    """Tests for generate_server method."""

    @pytest.fixture
    def generator(self):
        """Create ServerGenerator instance."""
        return ServerGenerator()

    @pytest.fixture
    def basic_spec(self):
        """Create basic tool spec."""
        return ToolSpec(
            name="test_tool",
            description="A test tool",
            input_schema={
                "type": "object",
                "properties": {"param": {"type": "string"}},
            },
        )

    def test_generate_server_basic(self, generator, basic_spec):
        """Test generating basic server."""
        code = generator.generate_server(
            server_name="TestServer",
            tool_specs=[basic_spec],
            implementations={"test_tool": '    return {"result": "ok"}'},
        )

        assert "TestServer" in code
        assert "FastMCP" in code
        assert "mcp.tool()" in code or "@mcp.tool" in code

    def test_generate_server_with_auth_env_vars(self, generator, basic_spec):
        """Test generating server with auth environment variables."""
        code = generator.generate_server(
            server_name="AuthServer",
            tool_specs=[basic_spec],
            implementations={"test_tool": "return {}"},
            auth_env_vars=["API_KEY", "SECRET_TOKEN"],
        )

        assert "API_KEY" in code
        assert "SECRET_TOKEN" in code
        assert "os.environ" in code or "getenv" in code

    def test_generate_server_with_health_check(self, generator, basic_spec):
        """Test generating server with health check."""
        code = generator.generate_server(
            server_name="HealthServer",
            tool_specs=[basic_spec],
            implementations={"test_tool": "return {}"},
            include_health_check=True,
        )

        assert "health" in code.lower()

    def test_generate_server_without_health_check(self, generator, basic_spec):
        """Test generating server without health check."""
        code = generator.generate_server(
            server_name="NoHealthServer",
            tool_specs=[basic_spec],
            implementations={"test_tool": "return {}"},
            include_health_check=False,
        )

        # Should still be valid code
        assert "FastMCP" in code

    def test_generate_server_with_dependencies(self, generator):
        """Test generating server with dependencies."""
        spec = ToolSpec(
            name="http_tool",
            description="Tool with dependencies",
            input_schema={"type": "object", "properties": {}},
            dependencies=["httpx", "pydantic"],
        )

        code = generator.generate_server(
            server_name="DepServer",
            tool_specs=[spec],
            implementations={"http_tool": "return {}"},
        )

        assert "httpx" in code
        assert "pydantic" in code

    def test_generate_server_with_production_config(self, generator, basic_spec):
        """Test generating server with production config."""
        prod_config = ProductionConfig(
            enable_logging=True,
            enable_metrics=True,
            enable_rate_limiting=True,
            enable_retries=True,
        )

        code = generator.generate_server(
            server_name="ProdServer",
            tool_specs=[basic_spec],
            implementations={"test_tool": "    return {}"},
            production_config=prod_config,
        )

        # Production code should be included
        assert "logging" in code.lower() or "Logger" in code

    def test_generate_server_multiple_tools(self, generator):
        """Test generating server with multiple tools."""
        specs = [
            ToolSpec("tool1", "First tool", {"type": "object", "properties": {}}),
            ToolSpec("tool2", "Second tool", {"type": "object", "properties": {}}),
            ToolSpec("tool3", "Third tool", {"type": "object", "properties": {}}),
        ]

        code = generator.generate_server(
            server_name="MultiServer",
            tool_specs=specs,
            implementations={
                "tool1": '    return {"name": "one"}',
                "tool2": '    return {"name": "two"}',
                "tool3": '    return {"name": "three"}',
            },
        )

        # The server should have multiple tool definitions
        assert "MultiServer" in code
        assert code.count("@mcp.tool") >= 3 or code.count("mcp.tool()") >= 3

    def test_generate_server_with_import_extraction(self, generator, basic_spec):
        """Test that imports are extracted from implementations."""
        impl_with_imports = """import json
import datetime
return json.dumps({"time": str(datetime.datetime.now())})"""

        code = generator.generate_server(
            server_name="ImportServer",
            tool_specs=[basic_spec],
            implementations={"test_tool": impl_with_imports},
        )

        assert "json" in code
        assert "datetime" in code


class TestGenerateServerSimple:
    """Tests for generate_server_simple method."""

    @pytest.fixture
    def generator(self):
        """Create ServerGenerator instance."""
        return ServerGenerator()

    def test_generate_simple_basic(self, generator):
        """Test basic simple server generation."""
        spec = ToolSpec(
            name="simple_tool",
            description="A simple tool",
            input_schema={"type": "object", "properties": {}},
        )

        code = generator.generate_server_simple(
            server_name="SimpleServer",
            tool_specs=[spec],
            implementations={"simple_tool": "    return {}"},
        )

        # Just verify it's valid server code
        assert "FastMCP" in code
        assert "@mcp.tool" in code or "mcp.tool()" in code

    def test_generate_simple_with_auth(self, generator):
        """Test simple server with auth vars."""
        spec = ToolSpec("auth_tool", "Auth tool", {"type": "object", "properties": {}})

        code = generator.generate_server_simple(
            server_name="AuthServer",
            tool_specs=[spec],
            implementations={"auth_tool": "return {}"},
            auth_env_vars=["AUTH_KEY"],
        )

        assert "AUTH_KEY" in code


class TestGenerateDependencyImports:
    """Tests for _generate_dependency_imports method."""

    @pytest.fixture
    def generator(self):
        """Create ServerGenerator instance."""
        return ServerGenerator()

    def test_empty_deps(self, generator):
        """Test with empty dependencies."""
        imports = generator._generate_dependency_imports(set())
        assert imports == []

    def test_single_dep(self, generator):
        """Test with single dependency."""
        imports = generator._generate_dependency_imports({"httpx"})
        assert any("httpx" in imp for imp in imports)

    def test_multiple_deps(self, generator):
        """Test with multiple dependencies."""
        imports = generator._generate_dependency_imports(
            {"httpx", "aiohttp", "pydantic"}
        )
        imports_str = "\n".join(imports)
        assert "httpx" in imports_str
        assert "aiohttp" in imports_str
        assert "pydantic" in imports_str


class TestExtractImports:
    """Tests for _extract_imports_from_implementation method."""

    @pytest.fixture
    def generator(self):
        """Create ServerGenerator instance."""
        return ServerGenerator()

    def test_no_imports(self, generator):
        """Test with code without imports."""
        imports, cleaned = generator._extract_imports_from_implementation(
            'return {"result": True}'
        )
        assert imports == []
        assert "return" in cleaned

    def test_simple_import(self, generator):
        """Test with simple import."""
        code = """import json
return json.dumps({})"""
        imports, cleaned = generator._extract_imports_from_implementation(code)
        assert "import json" in imports
        assert "import json" not in cleaned

    def test_from_import(self, generator):
        """Test with from import."""
        code = """from datetime import datetime
return str(datetime.now())"""
        imports, cleaned = generator._extract_imports_from_implementation(code)
        assert "from datetime import datetime" in imports
        assert "from datetime" not in cleaned

    def test_multiple_imports(self, generator):
        """Test with multiple imports."""
        code = """import json
import os
from pathlib import Path
return Path(os.getcwd())"""
        imports, cleaned = generator._extract_imports_from_implementation(code)
        assert len(imports) == 3
        assert "import json" not in cleaned
        assert "return" in cleaned


class TestValidateGeneratedCode:
    """Tests for _validate_generated_code method."""

    @pytest.fixture
    def generator(self):
        """Create ServerGenerator instance."""
        return ServerGenerator()

    def test_valid_code(self, generator):
        """Test with valid Python code."""
        code = """
def hello():
    return "Hello"

if __name__ == "__main__":
    print(hello())
"""
        is_valid = generator._validate_generated_code(code)
        assert is_valid is True

    def test_invalid_syntax(self, generator):
        """Test with invalid syntax."""
        code = """
def broken(
    return "missing paren"
"""
        is_valid = generator._validate_generated_code(code)
        assert is_valid is False

    def test_empty_code(self, generator):
        """Test with empty code."""
        is_valid = generator._validate_generated_code("")
        assert is_valid is True


class TestGenerateDockerfile:
    """Tests for generate_dockerfile method."""

    @pytest.fixture
    def generator(self):
        """Create ServerGenerator instance."""
        return ServerGenerator()

    @pytest.fixture
    def basic_spec(self):
        """Create basic tool spec."""
        return ToolSpec("test", "Test", {"type": "object", "properties": {}})

    def test_basic_dockerfile(self, generator, basic_spec):
        """Test generating basic Dockerfile."""
        dockerfile = generator.generate_dockerfile(
            tool_specs=[basic_spec],
        )

        assert "FROM python" in dockerfile
        assert "COPY" in dockerfile

    def test_dockerfile_with_deps(self, generator):
        """Test Dockerfile with dependencies."""
        spec = ToolSpec(
            name="dep_tool",
            description="Tool with deps",
            input_schema={"type": "object", "properties": {}},
            dependencies=["httpx", "pydantic"],
        )

        dockerfile = generator.generate_dockerfile(
            tool_specs=[spec],
        )

        assert "httpx" in dockerfile
        assert "pydantic" in dockerfile

    def test_dockerfile_with_auth_vars(self, generator, basic_spec):
        """Test Dockerfile with auth env vars."""
        dockerfile = generator.generate_dockerfile(
            tool_specs=[basic_spec],
            auth_env_vars=["API_KEY", "SECRET"],
        )

        assert "API_KEY" in dockerfile
        assert "SECRET" in dockerfile


class TestGeneratePyproject:
    """Tests for generate_pyproject method."""

    @pytest.fixture
    def generator(self):
        """Create ServerGenerator instance."""
        return ServerGenerator()

    @pytest.fixture
    def basic_spec(self):
        """Create basic tool spec."""
        return ToolSpec("test", "Test", {"type": "object", "properties": {}})

    def test_basic_pyproject(self, generator, basic_spec):
        """Test generating basic pyproject.toml."""
        pyproject = generator.generate_pyproject(
            server_name="TestServer",
            tool_specs=[basic_spec],
        )

        assert "[project]" in pyproject
        assert "test" in pyproject.lower()
        assert "python" in pyproject

    def test_pyproject_with_deps(self, generator):
        """Test pyproject with dependencies."""
        spec = ToolSpec(
            name="dep_tool",
            description="Tool with deps",
            input_schema={"type": "object", "properties": {}},
            dependencies=["httpx", "pydantic"],
        )

        pyproject = generator.generate_pyproject(
            server_name="DepServer",
            tool_specs=[spec],
        )

        assert "httpx" in pyproject
        assert "pydantic" in pyproject

    def test_pyproject_includes_mcp(self, generator, basic_spec):
        """Test that pyproject includes mcp dependency."""
        pyproject = generator.generate_pyproject(
            server_name="McpServer",
            tool_specs=[basic_spec],
        )

        assert "mcp" in pyproject


class TestGenerateGitHubActions:
    """Tests for generate_github_actions method."""

    @pytest.fixture
    def generator(self):
        """Create ServerGenerator instance."""
        return ServerGenerator()

    @pytest.fixture
    def basic_spec(self):
        """Create basic tool spec."""
        return ToolSpec("test", "Test", {"type": "object", "properties": {}})

    def test_basic_workflow(self, generator, basic_spec):
        """Test generating basic workflow."""
        workflow = generator.generate_github_actions(
            server_name="TestServer",
            tool_specs=[basic_spec],
        )

        assert "name:" in workflow
        assert "on:" in workflow
        assert "jobs:" in workflow
        assert "pytest" in workflow or "test" in workflow

    def test_workflow_with_env_vars(self, generator, basic_spec):
        """Test workflow with env vars."""
        workflow = generator.generate_github_actions(
            server_name="EnvServer",
            tool_specs=[basic_spec],
            auth_env_vars=["API_KEY"],
        )

        assert "API_KEY" in workflow or "secrets" in workflow.lower()
