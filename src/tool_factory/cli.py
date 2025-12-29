"""Command-line interface for MCP Tool Factory."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """MCP Tool Factory - Generate universal AI tools.

    Build MCP servers that work with Claude, OpenAI, Google ADK,
    LangChain, CrewAI, and any MCP-compatible client.
    """
    pass


@cli.command()
@click.argument("description")
@click.option(
    "--output",
    "-o",
    default="./servers",
    help="Output directory for generated files (default: ./servers)",
)
@click.option(
    "--name",
    "-n",
    default="GeneratedToolServer",
    help="Name for the MCP server",
)
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["claude_code", "anthropic", "openai", "google"]),
    default=None,
    help="LLM provider (auto-detects from env if not set)",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model to use (uses provider default if not set)",
)
@click.option(
    "--web-search",
    "-w",
    is_flag=True,
    default=False,
    help="Search the web for API docs and examples before generating",
)
@click.option(
    "--auth",
    "-a",
    multiple=True,
    help="Environment variable for API auth (e.g., --auth API_KEY --auth SECRET_TOKEN)",
)
@click.option(
    "--health-check/--no-health-check",
    default=True,
    help="Include health check endpoint (default: enabled)",
)
@click.option(
    "--logging/--no-logging",
    "enable_logging",
    default=True,
    help="Include structured JSON logging (default: enabled)",
)
@click.option(
    "--metrics/--no-metrics",
    "enable_metrics",
    default=False,
    help="Include Prometheus metrics endpoint (default: disabled)",
)
@click.option(
    "--rate-limit",
    type=int,
    default=None,
    help="Enable rate limiting with N requests per minute",
)
@click.option(
    "--retries/--no-retries",
    "enable_retries",
    default=True,
    help="Include retry patterns with exponential backoff (default: enabled)",
)
def generate(
    description: str,
    output: str,
    name: str,
    provider: str | None,
    model: str | None,
    web_search: bool,
    auth: tuple[str, ...],
    health_check: bool,
    enable_logging: bool,
    enable_metrics: bool,
    rate_limit: int | None,
    enable_retries: bool,
) -> None:
    """Generate MCP server from natural language description.

    DESCRIPTION is a natural language description of the tools you want.

    Examples:
        mcp-factory generate "Create a tool that fetches weather data"
        mcp-factory generate "Stock price API" --web-search  # Search web first
        mcp-factory generate "Weather API" --auth WEATHER_API_KEY  # With auth
        mcp-factory generate "API tools" --metrics --rate-limit 100  # Production
    """
    from tool_factory.agent import ToolFactoryAgent
    from tool_factory.config import FactoryConfig, LLMProvider, get_default_config

    # Build config
    if provider:
        provider_enum = LLMProvider(provider)
        config = FactoryConfig(provider=provider_enum)
    else:
        config = get_default_config()

    if model:
        config.model = model

    # Auto-create subdirectory with server name if using default servers directory
    output_path = Path(output)
    if (
        output == "./servers"
        or output.endswith("/servers")
        or output.endswith("\\servers")
    ):
        # Create subdirectory with lowercase server name
        server_dir_name = name.lower().replace(" ", "_").replace("-", "_")
        output_path = output_path / server_dir_name

    # Build production config
    from tool_factory.production import ProductionConfig

    production_config = ProductionConfig(
        enable_logging=enable_logging,
        enable_metrics=enable_metrics,
        enable_rate_limiting=rate_limit is not None,
        rate_limit_requests=rate_limit or 100,
        enable_retries=enable_retries,
    )

    # Build display info
    web_search_status = (
        "[green]enabled[/green]" if web_search else "[dim]disabled[/dim]"
    )
    health_check_status = (
        "[green]enabled[/green]" if health_check else "[dim]disabled[/dim]"
    )
    auth_status = f"[cyan]{', '.join(auth)}[/cyan]" if auth else "[dim]none[/dim]"

    # Production features status
    prod_features = []
    if enable_logging:
        prod_features.append("logging")
    if enable_metrics:
        prod_features.append("metrics")
    if rate_limit:
        prod_features.append(f"rate-limit({rate_limit}/min)")
    if enable_retries:
        prod_features.append("retries")
    prod_status = (
        f"[cyan]{', '.join(prod_features)}[/cyan]"
        if prod_features
        else "[dim]none[/dim]"
    )

    console.print(
        Panel(
            f"[bold blue]MCP Tool Factory[/bold blue]\n\n"
            f"Generating server: [green]{name}[/green]\n"
            f"Provider: [cyan]{config.provider.value}[/cyan]\n"
            f"Model: [cyan]{config.model}[/cyan]\n"
            f"Web search: {web_search_status}\n"
            f"Auth env vars: {auth_status}\n"
            f"Health check: {health_check_status}\n"
            f"Production: {prod_status}\n"
            f"Output directory: [yellow]{output_path}[/yellow]",
            title="Starting Generation",
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Initialize agent
        task = progress.add_task("Initializing agent...", total=None)
        agent = ToolFactoryAgent(config=config)

        # Optionally search web first
        if web_search:
            progress.update(task, description="Searching web for API docs...")

        # Extract specs
        progress.update(task, description="Extracting tool specifications...")
        result = agent.generate_from_description_sync(
            description,
            name,
            web_search=web_search,
            auth_env_vars=list(auth),
            include_health_check=health_check,
            production_config=production_config,
        )

        # Write files
        progress.update(task, description="Writing generated files...")
        result.write_to_directory(str(output_path))

        progress.update(task, description="Done!")

    # Show summary
    console.print()
    files_list = [
        f"  - {output_path}/server.py",
        f"  - {output_path}/tests/test_tools.py",
        f"  - {output_path}/README.md",
        f"  - {output_path}/skill.md",
        f"  - {output_path}/Dockerfile",
        f"  - {output_path}/pyproject.toml",
        f"  - {output_path}/.github/workflows/ci.yml [cyan](CI/CD)[/cyan]",
    ]
    # Add execution logs if available
    if result.execution_log:
        files_list.append(
            f"  - {output_path}/EXECUTION_LOG.md [green](full execution trace)[/green]"
        )
        files_list.append(
            f"  - {output_path}/execution_log.json [dim](machine-readable)[/dim]"
        )

    console.print(
        Panel(
            "[bold green]Successfully generated MCP server![/bold green]\n\n"
            "[bold]Tools created:[/bold]\n"
            + "\n".join(
                f"  - {spec.name}: {spec.description}" for spec in result.tool_specs
            )
            + "\n\n[bold]Files generated:[/bold]\n"
            + "\n".join(files_list),
            title="Generation Complete",
        )
    )

    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  1. cd {output}")
    console.print("  2. pip install -e .")
    console.print("  3. python server.py")
    console.print()
    console.print("[dim]Or add to Claude Code config:[/dim]")
    server_name = name.lower()
    server_path = f"{output_path}/server.py"
    mcp_config = (
        f'{{"mcpServers": {{"{server_name}": '
        f'{{"command": "python", "args": ["{server_path}"]}}}}}}'
    )
    console.print(f"  {mcp_config}")


@cli.command()
@click.argument("openapi_path", type=click.Path(exists=True))
@click.option(
    "--base-url",
    "-u",
    default=None,
    help="Base URL for the API (auto-detected from spec if not provided)",
)
@click.option(
    "--output",
    "-o",
    default="./servers",
    help="Output directory for generated files (default: ./servers)",
)
@click.option(
    "--name",
    "-n",
    default=None,
    help="Name for the MCP server (auto-generated from spec if not provided)",
)
def from_openapi(
    openapi_path: str, base_url: str | None, output: str, name: str | None
) -> None:
    """Generate MCP server from OpenAPI specification.

    OPENAPI_PATH is the path to an OpenAPI spec file (JSON or YAML).

    Features:
    - Auto-detects base URL from spec
    - Supports API Key, Bearer, OAuth2, and Basic auth
    - Handles request body parameters
    - Full error handling

    Examples:
        mcp-factory from-openapi petstore.yaml
        mcp-factory from-openapi api.json --base-url https://api.example.com
        mcp-factory from-openapi spec.yaml --name MyAPIServer
    """
    import yaml

    from tool_factory.agent import ToolFactoryAgent
    from tool_factory.openapi import OpenAPIParser

    # Load OpenAPI spec
    with open(openapi_path) as f:
        if openapi_path.endswith((".yaml", ".yml")):
            spec = yaml.safe_load(f)
        else:
            spec = json.load(f)

    # Parse spec for display info
    parser = OpenAPIParser(spec)
    info = parser.get_info()
    servers = parser.get_servers()
    auth_config = parser.get_auth_config()

    # Auto-generate name from spec if not provided
    if not name:
        api_title = info.get("title", "API")
        name = api_title.replace(" ", "").replace("-", "")[:30] + "Server"

    # Display detected info
    detected_url = servers[0]["url"] if servers else "not found"
    effective_url = base_url or detected_url
    auth_type = (
        auth_config.auth_type.value
        if auth_config.auth_type.value != "none"
        else "none detected"
    )

    # Auto-create subdirectory with server name
    output_path = Path(output)
    if (
        output == "./servers"
        or output.endswith("/servers")
        or output.endswith("\\servers")
    ):
        server_dir_name = name.lower().replace(" ", "_").replace("-", "_")
        output_path = output_path / server_dir_name

    console.print(
        Panel(
            f"[bold blue]MCP Tool Factory - OpenAPI[/bold blue]\n\n"
            f"[bold]Spec:[/bold] [green]{openapi_path}[/green]\n"
            f"[bold]API Title:[/bold] {info.get('title', 'Unknown')}\n"
            f"[bold]API Version:[/bold] {info.get('version', 'Unknown')}\n"
            f"[bold]Base URL:[/bold] [yellow]{effective_url}[/yellow]\n"
            f"[bold]Auth Type:[/bold] [cyan]{auth_type}[/cyan]\n"
            f"[bold]Server Name:[/bold] [green]{name}[/green]\n"
            f"[bold]Output:[/bold] [yellow]{output_path}[/yellow]",
            title="OpenAPI to MCP",
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing OpenAPI specification...", total=None)

        agent = ToolFactoryAgent()

        progress.update(task, description="Generating MCP server code...")
        import asyncio

        result = asyncio.run(agent.generate_from_openapi(spec, base_url, name))

        progress.update(task, description="Writing files...")
        result.write_to_directory(str(output_path))

        progress.update(task, description="Done!")

    # Show summary
    console.print()
    console.print(
        Panel(
            f"[bold green]Successfully generated MCP server![/bold green]\n\n"
            f"[bold]Endpoints converted:[/bold] {len(result.tool_specs)}\n\n"
            f"[bold]Tools:[/bold]\n"
            + "\n".join(f"  - {spec.name}" for spec in result.tool_specs[:10])
            + (
                f"\n  ... and {len(result.tool_specs) - 10} more"
                if len(result.tool_specs) > 10
                else ""
            ),
            title="Generation Complete",
        )
    )

    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  1. cd {output_path}")
    if auth_config.auth_type.value != "none":
        console.print(f"  2. export {auth_config.env_var_name}=your_api_key")
        console.print("  3. pip install -e .")
        console.print("  4. python server.py")
    else:
        console.print("  2. pip install -e .")
        console.print("  3. python server.py")


@cli.command()
@click.argument("database_path", type=click.Path(exists=True))
@click.option(
    "--type",
    "-t",
    "db_type",
    type=click.Choice(["sqlite", "postgresql"]),
    default="sqlite",
    help="Database type (default: sqlite)",
)
@click.option(
    "--output",
    "-o",
    default="./servers",
    help="Output directory for generated files (default: ./servers)",
)
@click.option(
    "--name",
    "-n",
    default=None,
    help="Name for the MCP server (auto-generated if not provided)",
)
@click.option(
    "--tables",
    "-T",
    multiple=True,
    help="Specific tables to include (default: all tables)",
)
def from_database(
    database_path: str,
    db_type: str,
    output: str,
    name: str | None,
    tables: tuple[str, ...],
) -> None:
    """Generate MCP server with CRUD tools from a database.

    DATABASE_PATH is the path to a SQLite database file, or a PostgreSQL connection string.

    Features:
    - Auto-generates CRUD tools for each table
    - get_<table>: Get record by primary key
    - list_<table>: List with filtering and pagination
    - create_<table>: Insert new records
    - update_<table>: Update existing records
    - delete_<table>: Delete records

    Examples:
        mcp-factory from-database ./myapp.db
        mcp-factory from-database ./data.db --name MyDataServer
        mcp-factory from-database ./app.db --tables users --tables orders
        mcp-factory from-database "postgresql://user:pass@host/db" --type postgresql
    """
    from tool_factory.database import (
        DatabaseIntrospector,
        DatabaseServerGenerator,
        DatabaseType,
    )
    from tool_factory.generators.docs import DocsGenerator
    from tool_factory.generators.server import ServerGenerator
    from tool_factory.models import GeneratedServer

    # Parse database type
    db_type_enum = (
        DatabaseType.SQLITE if db_type == "sqlite" else DatabaseType.POSTGRESQL
    )

    # Auto-generate name from database file
    if not name:
        if db_type == "sqlite":
            db_name = Path(database_path).stem
        else:
            # Extract database name from connection string
            db_name = database_path.split("/")[-1].split("?")[0]
        name = f"{db_name.title().replace('_', '').replace('-', '')}Server"

    # Auto-create subdirectory
    output_path = Path(output)
    if (
        output == "./servers"
        or output.endswith("/servers")
        or output.endswith("\\servers")
    ):
        server_dir_name = name.lower().replace(" ", "_").replace("-", "_")
        output_path = output_path / server_dir_name

    console.print(
        Panel(
            f"[bold blue]MCP Tool Factory - Database[/bold blue]\n\n"
            f"[bold]Database:[/bold] [green]{database_path}[/green]\n"
            f"[bold]Type:[/bold] [cyan]{db_type}[/cyan]\n"
            f"[bold]Server Name:[/bold] [green]{name}[/green]\n"
            f"[bold]Output:[/bold] [yellow]{output_path}[/yellow]",
            title="Database to MCP",
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Introspecting database schema...", total=None)

        # Introspect database
        introspector = DatabaseIntrospector(db_type_enum, database_path)
        all_tables = introspector.get_tables()

        # Filter tables if specified
        if tables:
            table_names = set(tables)
            filtered_tables = [t for t in all_tables if t.name in table_names]
        else:
            filtered_tables = all_tables

        if not filtered_tables:
            console.print("[bold red]No tables found in database![/bold red]")
            raise SystemExit(1)

        progress.update(
            task,
            description=f"Found {len(filtered_tables)} tables, generating server...",
        )

        # Generate server
        generator = DatabaseServerGenerator(
            db_type_enum, database_path, filtered_tables
        )
        server_code = generator.generate_server_code(name)
        tool_specs = generator.get_tool_specs()
        env_vars = generator.get_env_vars()

        # Generate other artifacts
        server_gen = ServerGenerator()
        docs_gen = DocsGenerator()

        progress.update(task, description="Writing files...")

        result = GeneratedServer(
            name=name,
            server_code=server_code,
            tool_specs=tool_specs,
            test_code=server_gen.generate_tests(tool_specs),
            dockerfile=server_gen.generate_dockerfile(tool_specs, env_vars),
            readme=docs_gen.generate_readme(name, tool_specs),
            skill_file=docs_gen.generate_skill(name, tool_specs),
            pyproject_toml=server_gen.generate_pyproject(name, tool_specs),
            github_actions=server_gen.generate_github_actions(
                name, tool_specs, env_vars
            ),
        )

        result.write_to_directory(str(output_path))
        progress.update(task, description="Done!")

    # Show summary
    console.print()

    # Group tools by table
    tables_summary = []
    for table in filtered_tables:
        pk = table.primary_key
        tools = ["list"]
        if pk:
            tools = ["get", "list", "create", "update", "delete"]
        tables_summary.append(
            f"  - {table.name} ({len(table.columns)} cols) → {', '.join(tools)}"
        )

    console.print(
        Panel(
            f"[bold green]Successfully generated MCP server![/bold green]\n\n"
            f"[bold]Tables:[/bold] {len(filtered_tables)}\n"
            f"[bold]Tools generated:[/bold] {len(tool_specs)}\n\n"
            + "\n".join(tables_summary),
            title="Generation Complete",
        )
    )

    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  1. cd {output_path}")
    if db_type == "postgresql":
        console.print("  2. export DATABASE_URL=postgresql://user:pass@host/db")
    else:
        console.print(f"  2. export DATABASE_PATH={database_path}")
    console.print("  3. pip install -e .")
    console.print("  4. python server.py")


@cli.command()
@click.argument("server_path", type=click.Path(exists=True))
def test(server_path: str) -> None:
    """Run tests for a generated MCP server.

    SERVER_PATH is the directory containing the generated server.

    Example:
        mcp-factory test ./generated
    """
    import subprocess

    console.print(f"[bold]Running tests for {server_path}...[/bold]")
    console.print()

    result = subprocess.run(
        ["pytest", "-v", f"{server_path}/tests"],
        capture_output=False,
    )

    if result.returncode == 0:
        console.print()
        console.print("[bold green]All tests passed![/bold green]")
    else:
        console.print()
        console.print("[bold red]Some tests failed.[/bold red]")

    raise SystemExit(result.returncode)


@cli.command()
@click.argument("server_path", type=click.Path(exists=True))
@click.option(
    "--transport",
    "-t",
    default="stdio",
    type=click.Choice(["stdio", "sse"]),
    help="MCP transport to use",
)
@click.option(
    "--port",
    "-p",
    default=8000,
    help="Port for SSE transport",
)
def serve(server_path: str, transport: str, port: int) -> None:
    """Start an MCP server for testing.

    SERVER_PATH is the directory containing server.py.

    Example:
        mcp-factory serve ./generated
        mcp-factory serve ./generated --transport sse --port 8080
    """
    import os
    import subprocess

    env = os.environ.copy()
    env["MCP_TRANSPORT"] = transport
    if transport == "sse":
        env["MCP_PORT"] = str(port)

    console.print("[bold]Starting MCP server...[/bold]")
    console.print(f"Transport: {transport}")
    if transport == "sse":
        console.print(f"Port: {port}")
    console.print()

    try:
        subprocess.run(
            ["python", f"{server_path}/server.py"],
            env=env,
        )
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Server stopped.[/yellow]")


@cli.command()
def info() -> None:
    """Show information about MCP Tool Factory."""
    console.print(
        Panel(
            "[bold blue]MCP Tool Factory[/bold blue] v0.2.0\n\n"
            "Generate universal MCP servers that work with:\n"
            "  - Claude Code & Claude Desktop\n"
            "  - OpenAI Agents SDK\n"
            "  - Google ADK\n"
            "  - LangChain & CrewAI\n"
            "  - Any MCP-compatible client\n\n"
            "[bold]Commands:[/bold]\n"
            "  generate      Create MCP server from natural language\n"
            "  from-openapi  Create MCP server from OpenAPI spec\n"
            "  from-database Create MCP server with CRUD tools from database\n"
            "  test          Run tests for generated server\n"
            "  serve         Start MCP server for testing\n\n"
            "[bold]Features:[/bold]\n"
            "  - Multi-provider LLM support (Anthropic, OpenAI, Google)\n"
            "  - Web search for API documentation\n"
            "  - OpenAPI with auth (API Key, Bearer, OAuth2)\n"
            "  - Database CRUD (SQLite, PostgreSQL)\n"
            "  - Health check endpoints\n"
            "  - GitHub Actions CI/CD\n"
            "  - Full execution logging\n\n"
            "[dim]https://github.com/hisham-maged/mcp-tool-factory[/dim]",
            title="About",
        )
    )


if __name__ == "__main__":
    cli()
