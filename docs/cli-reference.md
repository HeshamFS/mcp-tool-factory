# CLI Reference

Complete reference for the MCP Tool Factory command-line interface.

## Overview

```bash
mcp-factory [OPTIONS] COMMAND [ARGS]
```

### Global Options

| Option | Description |
|--------|-------------|
| `--version` | Show version number |
| `--help` | Show help message |

### Available Commands

| Command | Description |
|---------|-------------|
| `generate` | Generate MCP server from natural language |
| `from-openapi` | Generate MCP server from OpenAPI spec |
| `from-database` | Generate MCP server from database schema |
| `test` | Run tests for a generated server |
| `serve` | Start a server for testing |
| `info` | Show information about MCP Tool Factory |

---

## generate

Generate an MCP server from a natural language description.

### Synopsis

```bash
mcp-factory generate DESCRIPTION [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `DESCRIPTION` | Yes | Natural language description of the tools to generate |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--output` | `-o` | `./servers` | Output directory for generated files |
| `--name` | `-n` | `GeneratedToolServer` | Name for the MCP server |
| `--provider` | `-p` | Auto-detect | LLM provider: `claude_code`, `anthropic`, `openai`, `google` |
| `--model` | `-m` | Provider default | Model to use for generation |
| `--web-search` | `-w` | `false` | Search web for API documentation before generating |
| `--auth` | `-a` | None | Environment variable for API auth (repeatable) |
| `--health-check` | | `true` | Include health check endpoint |
| `--no-health-check` | | | Disable health check endpoint |
| `--logging` | | `true` | Include structured JSON logging |
| `--no-logging` | | | Disable logging |
| `--metrics` | | `false` | Include Prometheus metrics endpoint |
| `--no-metrics` | | | Disable metrics |
| `--rate-limit` | | None | Enable rate limiting (requests per minute) |
| `--retries` | | `true` | Include retry patterns with exponential backoff |
| `--no-retries` | | | Disable retry patterns |

### Examples

#### Basic Generation

```bash
mcp-factory generate "Create a tool that calculates compound interest"
```

#### With Custom Name and Output

```bash
mcp-factory generate "Currency converter tool" \
  --name CurrencyServer \
  --output ./my-servers
```

#### With Web Search

Research APIs before generating:

```bash
mcp-factory generate "Stock prices using Alpha Vantage API" --web-search
```

#### With API Key Injection

```bash
mcp-factory generate "Weather API" \
  --auth WEATHER_API_KEY \
  --auth BACKUP_API_KEY
```

#### With Production Features

```bash
mcp-factory generate "Production API tools" \
  --metrics \
  --rate-limit 100 \
  --logging
```

#### With Specific Provider

```bash
mcp-factory generate "Date utilities" \
  --provider openai \
  --model gpt-4.1
```

#### Minimal Server

```bash
mcp-factory generate "Simple calculator" \
  --no-health-check \
  --no-logging \
  --no-retries
```

### Output Structure

```
servers/<server-name>/
├── server.py              # FastMCP server
├── tests/
│   ├── __init__.py
│   └── test_tools.py      # Pytest tests
├── .github/
│   └── workflows/
│       └── ci.yml         # GitHub Actions
├── Dockerfile             # Container config
├── pyproject.toml         # Package config
├── README.md              # Usage docs
├── skill.md               # Claude Code skill
├── EXECUTION_LOG.md       # Full trace (if enabled)
└── execution_log.json     # Machine-readable log
```

---

## from-openapi

Generate an MCP server from an OpenAPI specification.

### Synopsis

```bash
mcp-factory from-openapi OPENAPI_PATH [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `OPENAPI_PATH` | Yes | Path to OpenAPI spec file (JSON or YAML) |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--base-url` | `-u` | Auto-detect | Base URL for the API |
| `--output` | `-o` | `./servers` | Output directory |
| `--name` | `-n` | Auto-generate | Server name |

### Examples

#### Basic Import

```bash
mcp-factory from-openapi ./petstore.yaml
```

#### With Custom Base URL

```bash
mcp-factory from-openapi ./api.json --base-url https://api.example.com/v2
```

#### With Custom Name

```bash
mcp-factory from-openapi ./spec.yaml --name MyAPIServer
```

### Supported Auth Types

The following authentication methods are auto-detected:

| Auth Type | Description |
|-----------|-------------|
| API Key | Header, query, or cookie |
| Bearer Token | JWT or OAuth2 bearer |
| OAuth2 | All OAuth2 flows |
| Basic Auth | HTTP Basic authentication |

### OpenAPI Requirements

- **Version**: OpenAPI 3.0.0 or higher
- **Required fields**: `openapi`, `info`, `paths`
- **Supported formats**: JSON, YAML

---

## from-database

Generate an MCP server with CRUD tools from a database schema.

### Synopsis

```bash
mcp-factory from-database DATABASE_PATH [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `DATABASE_PATH` | Yes | Path to SQLite file or PostgreSQL connection string |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--type` | `-t` | `sqlite` | Database type: `sqlite`, `postgresql` |
| `--output` | `-o` | `./servers` | Output directory |
| `--name` | `-n` | Auto-generate | Server name |
| `--tables` | `-T` | All tables | Specific tables to include (repeatable) |

### Examples

#### SQLite Database

```bash
mcp-factory from-database ./myapp.db
```

#### Specific Tables Only

```bash
mcp-factory from-database ./ecommerce.db \
  --tables products \
  --tables orders \
  --tables customers
```

#### PostgreSQL

```bash
mcp-factory from-database "postgresql://user:pass@localhost:5432/mydb" \
  --type postgresql \
  --name MyDBServer
```

### Generated CRUD Tools

For each table, the following tools are generated:

| Tool | Description |
|------|-------------|
| `get_<table>` | Get record by primary key |
| `list_<table>` | List with filtering and pagination |
| `create_<table>` | Insert new records |
| `update_<table>` | Update existing records |
| `delete_<table>` | Delete records |

### Example Output

For a `users` table:

```python
@mcp.tool()
def get_users(id: int) -> dict:
    """Get a user by ID."""
    ...

@mcp.tool()
def list_users(
    name: str = None,
    email: str = None,
    limit: int = 100,
    offset: int = 0
) -> dict:
    """List users with optional filtering."""
    ...

@mcp.tool()
def create_users(name: str, email: str, ...) -> dict:
    """Create a new user."""
    ...

@mcp.tool()
def update_users(id: int, name: str = None, email: str = None) -> dict:
    """Update an existing user."""
    ...

@mcp.tool()
def delete_users(id: int) -> dict:
    """Delete a user."""
    ...
```

---

## test

Run tests for a generated MCP server.

### Synopsis

```bash
mcp-factory test SERVER_PATH
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `SERVER_PATH` | Yes | Path to the generated server directory |

### Examples

```bash
mcp-factory test ./servers/my-server
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All tests passed |
| `1` | One or more tests failed |

---

## serve

Start an MCP server for testing.

### Synopsis

```bash
mcp-factory serve SERVER_PATH [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `SERVER_PATH` | Yes | Path to the server directory |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--transport` | `-t` | `stdio` | MCP transport: `stdio`, `sse` |
| `--port` | `-p` | `8000` | Port for SSE transport |

### Examples

#### Standard STDIO Transport

```bash
mcp-factory serve ./servers/my-server
```

#### SSE Transport

```bash
mcp-factory serve ./servers/my-server --transport sse --port 8080
```

### Stopping the Server

Press `Ctrl+C` to stop the server gracefully.

---

## info

Display information about MCP Tool Factory.

### Synopsis

```bash
mcp-factory info
```

### Output

Shows:
- Version number
- Available commands
- Supported features
- Supported frameworks

---

## Environment Variables

### LLM Provider Keys

| Variable | Provider |
|----------|----------|
| `ANTHROPIC_API_KEY` | Anthropic Claude |
| `OPENAI_API_KEY` | OpenAI GPT |
| `GOOGLE_API_KEY` | Google Gemini |
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code OAuth |

### Provider Selection

| Variable | Values |
|----------|--------|
| `MCP_FACTORY_PROVIDER` | `anthropic`, `openai`, `google`, `claude_code` |
| `MCP_FACTORY_MODEL` | Model ID (e.g., `claude-sonnet-4-5-20241022`) |

### Runtime Configuration

| Variable | Description |
|----------|-------------|
| `MCP_TRANSPORT` | Transport type for `serve` command |
| `MCP_PORT` | Port for SSE transport |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error or test failure |
| `2` | Invalid arguments |

---

## Tips

### Combine with Shell Commands

```bash
# Generate and immediately test
mcp-factory generate "Calculator" && mcp-factory test ./servers/generatedtoolserver

# Generate with timestamp in name
mcp-factory generate "API tools" --name "APIServer_$(date +%Y%m%d)"
```

### Use Shell Variables

```bash
DESCRIPTION="Create a tool that fetches stock prices"
mcp-factory generate "$DESCRIPTION" --web-search
```

### Batch Generation

```bash
# Generate multiple servers
for desc in "Weather API" "Stock API" "News API"; do
  name=$(echo "$desc" | tr ' ' '_')
  mcp-factory generate "$desc" --name "$name" --web-search
done
```
