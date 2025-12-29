"""Documentation generator for MCP Tool Factory."""

from tool_factory.models import ToolSpec


class DocsGenerator:
    """Generates documentation for MCP servers."""

    def _generate_overview_tagline(
        self,
        server_name: str,
        tool_specs: list[ToolSpec],
        description: str | None,
    ) -> str:
        """Generate a tagline for the server based on its tools."""
        if description and len(description) > 20:
            # Use first sentence of description as tagline
            first_sentence = description.split(".")[0].strip()
            if len(first_sentence) > 10:
                return first_sentence

        # Analyze tools to generate tagline
        tool_names = [spec.name for spec in tool_specs]
        tool_descriptions = [spec.description.lower() for spec in tool_specs]
        all_text = " ".join(tool_descriptions)

        # Detect common domains
        if any(word in all_text for word in ["weather", "temperature", "forecast", "climate"]):
            return "Weather and climate data tools for AI agents"
        elif any(word in all_text for word in ["database", "sql", "query", "crud", "table"]):
            return "Database operations and CRUD tools for AI agents"
        elif any(word in all_text for word in ["github", "repository", "commit", "pull request", "issue"]):
            return "GitHub integration tools for AI agents"
        elif any(word in all_text for word in ["iot", "device", "sensor", "thing", "ditto", "twin"]):
            return "IoT device management tools for AI agents"
        elif any(word in all_text for word in ["api", "rest", "http", "endpoint"]):
            return "REST API integration tools for AI agents"
        elif any(word in all_text for word in ["file", "document", "read", "write", "storage"]):
            return "File and document management tools for AI agents"
        elif any(word in all_text for word in ["email", "message", "notification", "send"]):
            return "Communication and messaging tools for AI agents"
        elif any(word in all_text for word in ["payment", "stripe", "transaction", "billing"]):
            return "Payment processing tools for AI agents"
        elif any(word in all_text for word in ["search", "find", "query", "lookup"]):
            return "Search and discovery tools for AI agents"
        elif any(word in all_text for word in ["user", "auth", "login", "account"]):
            return "User management and authentication tools for AI agents"
        else:
            return f"MCP tools for {server_name} operations"

    def _generate_overview_description(
        self,
        server_name: str,
        tool_specs: list[ToolSpec],
        description: str | None,
    ) -> str:
        """Generate a rich overview description."""
        tool_count = len(tool_specs)
        tool_names = [f"`{spec.name}`" for spec in tool_specs[:5]]
        tools_list = ", ".join(tool_names)
        if len(tool_specs) > 5:
            tools_list += f", and {len(tool_specs) - 5} more"

        base_desc = description or f"An MCP server providing {tool_count} tools for various operations."

        overview = f"""An MCP (Model Context Protocol) server that enables AI agents to perform specialized operations through a standardized interface.

**{server_name}** provides {tool_count} tools including {tools_list}.

{base_desc}"""
        return overview

    def _generate_tools_summary_table(self, tool_specs: list[ToolSpec]) -> list[str]:
        """Generate a summary table of all tools."""
        parts = [
            "## Tools Overview",
            "",
            "| Tool | Description |",
            "|------|-------------|",
        ]

        for spec in tool_specs:
            # Truncate description to first sentence or 60 chars
            desc = spec.description.split(".")[0].strip()
            if len(desc) > 60:
                desc = desc[:57] + "..."
            parts.append(f"| `{spec.name}` | {desc} |")

        parts.append("")
        return parts

    def _generate_architecture_diagram(
        self,
        server_name: str,
        tool_specs: list[ToolSpec],
    ) -> list[str]:
        """Generate a Mermaid architecture diagram."""
        # Group tools by prefix/category
        tool_names = [spec.name for spec in tool_specs[:8]]  # Limit for readability

        parts = [
            "## Architecture",
            "",
            "```mermaid",
            "flowchart LR",
            '    subgraph Agents["AI Agents"]',
            "        A[Claude / GPT / LangChain]",
            "    end",
            "",
            f'    subgraph Server["{server_name}"]',
        ]

        # Add tool nodes
        for i, name in enumerate(tool_names):
            parts.append(f"        T{i}[{name}]")

        parts.extend([
            "    end",
            "",
            '    subgraph Output["Results"]',
            "        R[Structured Data / Actions]",
            "    end",
            "",
            "    Agents --> Server",
            "    Server --> Output",
            "```",
            "",
        ])

        return parts

    def _generate_flow_diagram(
        self,
        server_name: str,
        tool_specs: list[ToolSpec],
    ) -> list[str]:
        """Generate a Mermaid flow diagram showing how the server works."""
        parts = [
            "## How It Works",
            "",
            "```mermaid",
            "sequenceDiagram",
            "    participant Agent as AI Agent",
            f"    participant Server as {server_name}",
            "    participant Target as External Service/Data",
            "",
            "    Agent->>Server: Tool call with parameters",
            "    Server->>Server: Validate inputs",
            "    Server->>Target: Execute operation",
            "    Target-->>Server: Return result",
            "    Server-->>Agent: Structured response",
            "```",
            "",
        ]

        return parts

    def generate_readme(
        self,
        server_name: str,
        tool_specs: list[ToolSpec],
        auth_env_vars: list[str] | None = None,
        description: str | None = None,
    ) -> str:
        """
        Generate README.md for the server.

        Args:
            server_name: Name of the MCP server
            tool_specs: List of tool specifications
            auth_env_vars: List of required environment variables
            description: Optional server description

        Returns:
            README content as string
        """
        server_slug = server_name.lower().replace(" ", "-")

        # Generate rich content
        tagline = self._generate_overview_tagline(server_name, tool_specs, description)
        overview = self._generate_overview_description(server_name, tool_specs, description)

        parts = [
            f"# {server_name}",
            "",
            f"**{tagline}**",
            "",
            "---",
            "",
            "## Overview",
            "",
            overview,
            "",
        ]

        # Add architecture diagram
        parts.extend(self._generate_architecture_diagram(server_name, tool_specs))

        # Add flow diagram
        parts.extend(self._generate_flow_diagram(server_name, tool_specs))

        # Add tools summary table
        parts.extend(self._generate_tools_summary_table(tool_specs))

        # Quick Start section
        parts.extend([
            "---",
            "",
            "## Quick Start",
            "",
            "```bash",
            "# Install dependencies",
            "pip install -e .",
            "",
            "# Run the server",
            "python server.py",
            "```",
            "",
        ])

        # Environment variables section
        if auth_env_vars:
            parts.extend([
                "## Environment Variables",
                "",
                "Create a `.env` file or set these environment variables:",
                "",
                "```bash",
            ])
            for var in auth_env_vars:
                parts.append(f"export {var}=your-api-key-here")
            parts.extend(["```", ""])

        parts.extend([
            "## Installation",
            "",
            "```bash",
            "pip install -e .",
            "```",
            "",
            "## Usage",
            "",
            "### With Claude Code / Claude Desktop",
            "",
            "Add to your `.claude/mcp.json`:",
            "",
            "```json",
            "{",
            '  "mcpServers": {',
            f'    "{server_slug}": {{',
            '      "command": "python",',
            '      "args": ["./server.py"]',
        ])

        # Add env vars to Claude config if present
        if auth_env_vars:
            parts.append('      "env": {')
            for i, var in enumerate(auth_env_vars):
                comma = "," if i < len(auth_env_vars) - 1 else ""
                parts.append(f'        "{var}": "${{env:{var}}}"{comma}')
            parts.append("      }")

        parts.extend([
            "    }",
            "  }",
            "}",
            "```",
            "",
            "### With OpenAI Agents SDK",
            "",
            "```python",
            "from agents import Agent",
            "from agents.mcp import MCPServerStdio",
            "",
            "async with MCPServerStdio(",
            '    command="python",',
            '    args=["./server.py"],',
        ])

        if auth_env_vars:
            parts.append("    env={")
            for var in auth_env_vars:
                parts.append(f'        "{var}": os.environ["{var}"],')
            parts.append("    },")

        parts.extend([
            ") as mcp_server:",
            "    agent = Agent(",
            f'        name="{server_name}",',
            "        mcp_servers=[mcp_server]",
            "    )",
            "```",
            "",
            "### With LangChain",
            "",
            "```python",
            "from langchain_mcp_adapters import load_mcp_tools",
            "",
            "tools = await load_mcp_tools(",
            '    command="python",',
            '    args=["./server.py"]',
            ")",
            "agent = create_react_agent(llm, tools)",
            "```",
            "",
            "### With Docker",
            "",
            "```bash",
            "# Build",
            f"docker build -t {server_slug} .",
            "",
            "# Run",
        ])

        if auth_env_vars:
            env_flags = " ".join([f"-e {var}" for var in auth_env_vars])
            parts.append(f"docker run {env_flags} {server_slug}")
        else:
            parts.append(f"docker run {server_slug}")

        parts.extend([
            "```",
            "",
            "---",
            "",
            "## Tool Reference",
            "",
        ])

        # Add tool documentation
        for spec in tool_specs:
            parts.append(f"### `{spec.name}`")
            parts.append("")
            parts.append(spec.description)
            parts.append("")

            # Parameters
            if spec.input_schema.get("properties"):
                parts.append("**Parameters:**")
                parts.append("")
                parts.append("| Name | Type | Required | Description |")
                parts.append("|------|------|----------|-------------|")
                for param_name, param_schema in spec.input_schema["properties"].items():
                    param_type = param_schema.get("type", "any")
                    param_desc = param_schema.get("description", "")
                    required = param_name in spec.input_schema.get("required", [])
                    req_str = "Yes" if required else "No"
                    parts.append(f"| `{param_name}` | {param_type} | {req_str} | {param_desc} |")
                parts.append("")

            # Output
            if spec.output_schema and spec.output_schema.get("properties"):
                parts.append("**Returns:**")
                parts.append("")
                for field_name, field_schema in spec.output_schema["properties"].items():
                    field_type = field_schema.get("type", "any")
                    field_desc = field_schema.get("description", "")
                    parts.append(f"- `{field_name}` ({field_type}): {field_desc}")
                parts.append("")

            # Example usage
            parts.append("**Example:**")
            parts.append("")
            parts.append("```python")
            if spec.input_schema.get("properties"):
                example_args = []
                for param_name, param_schema in spec.input_schema["properties"].items():
                    param_type = param_schema.get("type", "string")
                    if param_type == "string":
                        example_args.append(f'{param_name}="example"')
                    elif param_type == "integer":
                        example_args.append(f"{param_name}=1")
                    elif param_type == "number":
                        example_args.append(f"{param_name}=1.0")
                    elif param_type == "boolean":
                        example_args.append(f"{param_name}=True")
                    elif param_type == "object":
                        example_args.append(f"{param_name}={{...}}")
                    elif param_type == "array":
                        example_args.append(f"{param_name}=[...]")
                    else:
                        example_args.append(f'{param_name}="value"')
                parts.append(f"result = {spec.name}({', '.join(example_args[:3])})")
            else:
                parts.append(f"result = {spec.name}()")
            parts.append("```")
            parts.append("")
            parts.append("---")
            parts.append("")

        # Add testing section
        parts.extend([
            "## Testing",
            "",
            "```bash",
            "pytest tests/",
            "```",
            "",
            "---",
            "",
            "## License",
            "",
            "MIT",
            "",
        ])

        return "\n".join(parts)

    def generate_skill(self, server_name: str, tool_specs: list[ToolSpec]) -> str:
        """
        Generate Claude Code skill file.

        Args:
            server_name: Name of the MCP server
            tool_specs: List of tool specifications

        Returns:
            Skill file content as string
        """
        tagline = self._generate_overview_tagline(server_name, tool_specs, None)

        parts = [
            f"# {server_name}",
            "",
            tagline,
            "",
            "## Overview",
            "",
            f"This MCP server provides {len(tool_specs)} tools for AI agents.",
            "",
            "## Available Tools",
            "",
        ]

        for spec in tool_specs:
            parts.append(f"### {spec.name}")
            parts.append("")
            parts.append(spec.description)
            parts.append("")

            if spec.input_schema.get("properties"):
                parts.append("**Parameters:**")
                for param_name, param_schema in spec.input_schema["properties"].items():
                    param_desc = param_schema.get("description", "No description")
                    required = param_name in spec.input_schema.get("required", [])
                    req_str = " (required)" if required else " (optional)"
                    parts.append(f"- `{param_name}`{req_str}: {param_desc}")
                parts.append("")

            parts.append("**Example:**")
            parts.append("```")
            parts.append(f"Use the {spec.name} tool to {spec.description.lower()}")
            parts.append("```")
            parts.append("")

        # Setup instructions
        parts.extend([
            "## Setup",
            "",
            "Add to your Claude Code MCP configuration:",
            "",
            "```json",
            "{",
            '  "mcpServers": {',
            f'    "{server_name.lower().replace(" ", "-")}": {{',
            '      "command": "python",',
            '      "args": ["path/to/server.py"]',
            "    }",
            "  }",
            "}",
            "```",
            "",
        ])

        return "\n".join(parts)
