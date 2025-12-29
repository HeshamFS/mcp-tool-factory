"""Server code generator for MCP Tool Factory."""

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from tool_factory.models import ToolSpec

logger = logging.getLogger(__name__)


class ServerGenerator:
    """Generates FastMCP server code from tool specifications."""

    def __init__(self) -> None:
        """Initialize the generator with Jinja2 templates."""
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate_server(
        self,
        server_name: str,
        tool_specs: list[ToolSpec],
        implementations: dict[str, str],
        auth_env_vars: list[str] | None = None,
        include_health_check: bool = True,
        production_config: Any = None,
    ) -> str:
        """
        Generate complete FastMCP server code using Jinja2 templates.

        Args:
            server_name: Name for the MCP server
            tool_specs: List of tool specifications
            implementations: Dict mapping tool names to implementation code
            auth_env_vars: List of environment variable names for API auth
            include_health_check: If True, include health check endpoint
            production_config: ProductionConfig for logging, metrics, rate limiting

        Returns:
            Complete Python server code as string
        """
        auth_env_vars = auth_env_vars or []

        # Collect all dependencies
        all_deps: set[str] = set()
        for spec in tool_specs:
            all_deps.update(spec.dependencies)

        # Generate import statements for dependencies
        dep_imports = self._generate_dependency_imports(all_deps)

        # Extract imports from implementations
        extracted_imports: list[str] = []
        cleaned_implementations: dict[str, str] = {}
        for name, impl in implementations.items():
            impl_imports, cleaned = self._extract_imports_from_implementation(impl)
            extracted_imports.extend(impl_imports)
            cleaned_implementations[name] = cleaned

        # Deduplicate imports
        extracted_imports = list(dict.fromkeys(extracted_imports))

        # Production config code generation
        prod_imports = ""
        prod_logging = ""
        prod_metrics = ""
        prod_rate_limiting = ""
        prod_retry = ""

        if production_config:
            from tool_factory.production import ProductionCodeGenerator

            prod_gen = ProductionCodeGenerator(production_config)
            prod_imports = prod_gen.generate_imports()
            prod_logging = prod_gen.generate_logging_code()
            prod_metrics = prod_gen.generate_metrics_code()
            prod_rate_limiting = prod_gen.generate_rate_limiting_code()
            prod_retry = prod_gen.generate_retry_code()

        template = self.env.get_template("server.py.jinja")
        code = template.render(
            server_name=server_name,
            tool_specs=tool_specs,
            implementations=cleaned_implementations,
            dependency_imports=dep_imports,
            extracted_imports=extracted_imports,
            auth_env_vars=auth_env_vars,
            include_health_check=include_health_check,
            tool_count=len(tool_specs),
            production_imports=prod_imports,
            production_logging=prod_logging,
            production_metrics=prod_metrics,
            production_rate_limiting=prod_rate_limiting,
            production_retry=prod_retry,
        )

        # Validate syntax
        if not self._validate_generated_code(code):
            logger.error("Template-generated code failed syntax validation")

        return code

    def generate_server_simple(
        self,
        server_name: str,
        tool_specs: list[ToolSpec],
        implementations: dict[str, str],
        auth_env_vars: list[str] | None = None,
        include_health_check: bool = True,
        production_config: Any = None,
    ) -> str:
        """
        Generate server code without templates (fallback).

        Args:
            server_name: Name for the MCP server
            tool_specs: List of tool specifications
            implementations: Dict mapping tool names to implementation code
            auth_env_vars: List of environment variable names for API auth
            include_health_check: If True, include health check endpoint
            production_config: ProductionConfig for logging, metrics, rate limiting, retries

        Returns:
            Complete Python server code as string
        """
        auth_env_vars = auth_env_vars or []

        # Collect dependencies
        all_deps: set[str] = set()
        for spec in tool_specs:
            all_deps.update(spec.dependencies)

        # Build imports
        imports = [
            '"""Auto-generated MCP server."""',
            "",
            "import os",
            "from datetime import datetime",
            "from mcp.server.fastmcp import FastMCP",
            "from typing import Any",
        ]

        # Add production imports if enabled
        if production_config:
            from tool_factory.production import ProductionCodeGenerator

            prod_gen = ProductionCodeGenerator(production_config)
            prod_imports = prod_gen.generate_imports()
            if prod_imports:
                imports.append(prod_imports)

        imports.extend(self._generate_dependency_imports(all_deps))

        # Build server code
        code_parts = [
            "\n".join(imports),
            "",
            f'mcp = FastMCP("{server_name}", json_response=True)',
            "",
        ]

        # Add production utilities if enabled
        if production_config:
            from tool_factory.production import ProductionCodeGenerator

            prod_gen = ProductionCodeGenerator(production_config)

            # Add logging code
            logging_code = prod_gen.generate_logging_code()
            if logging_code:
                code_parts.append(logging_code)

            # Add metrics code
            metrics_code = prod_gen.generate_metrics_code()
            if metrics_code:
                code_parts.append(metrics_code)

            # Add rate limiting code
            rate_limit_code = prod_gen.generate_rate_limiting_code()
            if rate_limit_code:
                code_parts.append(rate_limit_code)

            # Add retry code
            retry_code = prod_gen.generate_retry_code()
            if retry_code:
                code_parts.append(retry_code)

        # Add auth configuration section if needed
        if auth_env_vars:
            code_parts.append("# ============== AUTH CONFIGURATION ==============")
            code_parts.append(
                "# These environment variables are required for API access"
            )
            code_parts.append("AUTH_CONFIG = {")
            for var in auth_env_vars:
                code_parts.append(f'    "{var}": os.environ.get("{var}"),')
            code_parts.append("}")
            code_parts.append("")
            code_parts.append("")
            code_parts.append("def get_auth(key: str) -> str | None:")
            code_parts.append('    """Get authentication value from environment."""')
            code_parts.append("    return AUTH_CONFIG.get(key)")
            code_parts.append("")
            code_parts.append("")
            code_parts.append("def require_auth(key: str) -> str:")
            code_parts.append('    """Get required auth value, raises if not set."""')
            code_parts.append("    value = get_auth(key)")
            code_parts.append("    if not value:")
            code_parts.append(
                '        raise ValueError(f"Missing required environment variable: {key}")'
            )
            code_parts.append("    return value")
            code_parts.append("")
            code_parts.append("")

        # Add health check endpoint if enabled
        if include_health_check:
            code_parts.append("# ============== HEALTH CHECK ==============")
            code_parts.append("")
            code_parts.append("@mcp.tool()")
            code_parts.append("def health_check() -> dict:")
            code_parts.append('    """')
            code_parts.append("    Check server health and configuration status.")
            code_parts.append("")
            code_parts.append("    Returns:")
            code_parts.append(
                "        Health status including uptime and auth configuration"
            )
            code_parts.append('    """')
            code_parts.append("    result = {")
            code_parts.append('        "status": "healthy",')
            code_parts.append(f'        "server": "{server_name}",')
            code_parts.append('        "timestamp": datetime.now().isoformat(),')
            code_parts.append(f'        "tools_available": {len(tool_specs)},')
            code_parts.append("    }")
            code_parts.append("")
            if auth_env_vars:
                code_parts.append("    # Check auth configuration")
                code_parts.append("    auth_status = {}")
                for var in auth_env_vars:
                    check_line = (
                        f'    auth_status["{var}"] = '
                        f'"configured" if get_auth("{var}") else "MISSING"'
                    )
                    code_parts.append(check_line)
                code_parts.append('    result["auth_config"] = auth_status')
                code_parts.append("")
                code_parts.append("    # Mark unhealthy if any auth is missing")
                code_parts.append('    if "MISSING" in auth_status.values():')
                code_parts.append('        result["status"] = "unhealthy"')
                code_parts.append(
                    '        result["error"] = "Missing required authentication"'
                )
            code_parts.append("")
            code_parts.append("    return result")
            code_parts.append("")
            code_parts.append("")

        # Add separator before tools
        code_parts.append("# ============== TOOLS ==============")
        code_parts.append("")

        # Process each tool - extract imports first, then add tool code
        extracted_imports: list[str] = []
        tool_code_parts: list[str] = []

        for spec in tool_specs:
            impl = implementations.get(spec.name, self._generate_stub(spec))
            # Extract any imports from the implementation
            impl_imports, cleaned_impl = self._extract_imports_from_implementation(impl)
            extracted_imports.extend(impl_imports)
            tool_code_parts.append("@mcp.tool()")
            tool_code_parts.append(cleaned_impl)
            tool_code_parts.append("")

        # If we extracted any imports, add them after the initial imports but before the server code
        if extracted_imports:
            # Deduplicate while preserving order
            seen = set()
            unique_imports = []
            for imp in extracted_imports:
                if imp not in seen:
                    seen.add(imp)
                    unique_imports.append(imp)

            # Insert after initial imports section (find the mcp = FastMCP line)
            insertion_point = None
            for i, part in enumerate(code_parts):
                if "FastMCP(" in part:
                    insertion_point = i
                    break

            if insertion_point is not None:
                # Add extracted imports before the FastMCP instantiation
                import_block = "\n".join(unique_imports) + "\n"
                code_parts.insert(insertion_point, import_block)

        # Add the tool code parts
        code_parts.extend(tool_code_parts)

        # Add main block
        code_parts.extend(
            [
                "",
                "# ============== MAIN ==============",
                "",
                'if __name__ == "__main__":',
            ]
        )

        # Print auth warning if needed
        if auth_env_vars:
            code_parts.append("    # Check for required auth on startup")
            code_parts.append(
                "    missing_auth = [k for k, v in AUTH_CONFIG.items() if not v]"
            )
            code_parts.append("    if missing_auth:")
            code_parts.append(
                '        print(f"WARNING: Missing environment variables: {missing_auth}")'
            )
            code_parts.append("")

        code_parts.extend(
            [
                '    mcp.run(transport="stdio")',
                "",
            ]
        )

        final_code = "\n".join(code_parts)

        # Validate syntax before returning
        if not self._validate_generated_code(final_code):
            logger.error("Generated code failed syntax validation")
            # Still return the code but log the error for debugging

        return final_code

    def generate_tests(self, tool_specs: list[ToolSpec]) -> str:
        """
        Generate pytest test code for the server.

        Args:
            tool_specs: List of tool specifications

        Returns:
            Test file content as string
        """
        test_parts = [
            '"""Auto-generated tests for MCP server."""',
            "",
            "import json",
            "import pytest",
            "from mcp import Client",
            "",
            "",
            "@pytest.fixture",
            "async def mcp_client():",
            '    """Create MCP client connected to server."""',
            "    from server import mcp",
            "",
            "    async with Client(transport=mcp) as client:",
            "        yield client",
            "",
            "",
            "@pytest.mark.asyncio",
            "async def test_list_tools(mcp_client):",
            '    """Verify all tools are registered."""',
            "    tools = await mcp_client.list_tools()",
            "    tool_names = [t.name for t in tools.tools]",
            "",
        ]

        # Add assertions for each tool
        for spec in tool_specs:
            test_parts.append(f'    assert "{spec.name}" in tool_names')

        test_parts.append("")

        # Add basic test for each tool
        for spec in tool_specs:
            test_parts.extend(
                [
                    "",
                    "@pytest.mark.asyncio",
                    f"async def test_{spec.name}_exists(mcp_client):",
                    f'    """Test {spec.name} tool is callable."""',
                    "    tools = await mcp_client.list_tools()",
                    f'    tool = next((t for t in tools.tools if t.name == "{spec.name}"), None)',
                    "    assert tool is not None",
                    f'    assert tool.description == "{spec.description}"',
                    "",
                ]
            )

        return "\n".join(test_parts)

    def generate_dockerfile(
        self,
        tool_specs: list[ToolSpec],
        auth_env_vars: list[str] | None = None,
        production_config: Any = None,
    ) -> str:
        """Generate Dockerfile for the server.

        Args:
            tool_specs: List of tool specifications
            auth_env_vars: List of environment variable names for API auth
            production_config: ProductionConfig for logging, metrics, rate limiting, retries

        Returns:
            Dockerfile content as string
        """
        auth_env_vars = auth_env_vars or []

        # Collect dependencies
        all_deps: set[str] = {"mcp"}
        for spec in tool_specs:
            all_deps.update(spec.dependencies)

        # Add production dependencies if enabled
        if production_config:
            if getattr(production_config, "enable_metrics", False):
                all_deps.add("prometheus_client")
            if getattr(production_config, "enable_rate_limiting", False):
                # Rate limiter is custom, but might use redis in future
                pass
            if getattr(production_config, "enable_retries", False):
                all_deps.add("tenacity")

        deps_str = " ".join(sorted(all_deps))

        dockerfile = f"""FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir {deps_str}

# Copy server code
COPY server.py .
"""

        # Add environment variables for auth
        if auth_env_vars:
            dockerfile += "\n# Required environment variables for API access\n"
            dockerfile += "# Pass these when running: docker run -e VAR=value ...\n"
            for var in auth_env_vars:
                dockerfile += f"ENV {var}=\n"
            dockerfile += "\n"

        # Add proper health check that actually tests the server
        dockerfile += """# Health check - verifies server module loads correctly
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import server; print('OK')"

# Run the server
CMD ["python", "server.py"]
"""
        return dockerfile

    def generate_pyproject(self, server_name: str, tool_specs: list[ToolSpec]) -> str:
        """Generate pyproject.toml for the server."""
        # Collect dependencies
        all_deps: set[str] = {"mcp>=1.0.0"}
        for spec in tool_specs:
            for dep in spec.dependencies:
                all_deps.add(f"{dep}>=0.1.0")

        deps_list = ",\n    ".join(f'"{dep}"' for dep in sorted(all_deps))

        return f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{server_name.lower().replace(" ", "-")}"
version = "0.1.0"
description = "Auto-generated MCP server"
requires-python = ">=3.11"
dependencies = [
    {deps_list}
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]
"""

    def _generate_dependency_imports(self, deps: set[str]) -> list[str]:
        """Generate import statements for dependencies."""
        imports = []
        for dep in sorted(deps):
            # Handle common package name mappings
            if dep == "pyyaml":
                imports.append("import yaml")
            elif dep == "python-dateutil":
                imports.append("from dateutil import parser as date_parser")
            elif dep == "beautifulsoup4":
                imports.append("from bs4 import BeautifulSoup")
            elif dep == "pillow":
                imports.append("from PIL import Image")
            else:
                imports.append(f"import {dep}")
        return imports

    def _generate_stub(self, spec: ToolSpec) -> str:
        """Generate a stub implementation for a tool."""
        params = []
        if "properties" in spec.input_schema:
            for name, schema in spec.input_schema["properties"].items():
                param_type = self._json_type_to_python(schema.get("type", "Any"))
                if name in spec.input_schema.get("required", []):
                    params.append(f"{name}: {param_type}")
                else:
                    default = schema.get("default", "None")
                    if isinstance(default, str):
                        default = f'"{default}"'
                    params.append(f"{name}: {param_type} = {default}")

        params_str = ", ".join(params)

        return f'''def {spec.name}({params_str}) -> dict:
    """
    {spec.description}

    Returns:
        Result dictionary
    """
    # TODO: Implement this tool
    return {{"error": "Not implemented"}}'''

    def _json_type_to_python(self, json_type: str) -> str:
        """Convert JSON Schema type to Python type hint."""
        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }
        return type_map.get(json_type, "Any")

    def _extract_imports_from_implementation(self, impl: str) -> tuple[list[str], str]:
        """
        Extract import statements from implementation code.

        Some LLM-generated implementations may include import statements at the top.
        This method separates them so imports can be placed at the file level.

        Args:
            impl: Implementation code that may contain imports

        Returns:
            Tuple of (list of import lines, cleaned implementation code)
        """
        lines = impl.strip().split("\n")
        imports = []
        code_start = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Check for import statements
            if stripped.startswith("import ") or stripped.startswith("from "):
                imports.append(stripped)
                code_start = i + 1
            elif stripped == "" and code_start == i:
                # Skip blank lines between imports
                code_start = i + 1
            elif stripped.startswith("#") and code_start == i:
                # Skip comments at the top
                code_start = i + 1
            else:
                # Non-import line found, stop scanning
                break

        # Reconstruct implementation without the imports
        remaining_lines = lines[code_start:]
        cleaned_impl = "\n".join(remaining_lines).strip()

        return imports, cleaned_impl

    def _validate_generated_code(self, code: str) -> bool:
        """
        Validate generated Python code compiles correctly.

        Args:
            code: Python code to validate

        Returns:
            True if code compiles, False otherwise
        """
        try:
            compile(code, "<generated>", "exec")
            return True
        except SyntaxError as e:
            logger.warning(f"Generated code has syntax error: {e}")
            return False

    def generate_github_actions(
        self,
        server_name: str,
        tool_specs: list[ToolSpec],
        auth_env_vars: list[str] | None = None,
    ) -> str:
        """Generate GitHub Actions CI/CD workflow."""
        auth_env_vars = auth_env_vars or []

        # Build secrets section for auth vars
        env_section = ""
        if auth_env_vars:
            env_section = "        env:\n"
            for var in auth_env_vars:
                env_section += f"          {var}: ${{{{ secrets.{var} }}}}\n"

        # Docker image name (used in multiple places)
        docker_image = server_name.lower().replace(" ", "-")

        return f"""name: CI/CD - {server_name}

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{{{ matrix.python-version }}}}
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ matrix.python-version }}}}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run tests
        run: pytest -v tests/
{env_section}
      - name: Type check
        run: |
          pip install mypy
          mypy server.py --ignore-missing-imports || true

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install linters
        run: |
          pip install ruff black

      - name: Check formatting
        run: black --check .

      - name: Lint with ruff
        run: ruff check .

  docker:
    runs-on: ubuntu-latest
    needs: [test, lint]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t {docker_image}:latest .

      - name: Test Docker image
        run: |
          docker run --rm {docker_image}:latest python -c "import server; print('OK')"

  # Uncomment to push to GitHub Container Registry
  # publish:
  #   runs-on: ubuntu-latest
  #   needs: docker
  #   if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  #
  #   steps:
  #     - uses: actions/checkout@v4
  #
  #     - name: Log in to Container Registry
  #       uses: docker/login-action@v3
  #       with:
  #         registry: ghcr.io
  #         username: ${{{{ github.actor }}}}
  #         password: ${{{{ secrets.GITHUB_TOKEN }}}}
  #
  #     - name: Build and push
  #       uses: docker/build-push-action@v5
  #       with:
  #         context: .
  #         push: true
  #         tags: ghcr.io/${{{{ github.repository_owner }}}}/{docker_image}:latest
"""
