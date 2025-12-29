# MCP Tool Factory

Generate universal MCP servers that work with **any** AI agent framework.

Build once, run everywhere: Claude, OpenAI, Google ADK, LangChain, CrewAI, and more.

## Why MCP?

MCP (Model Context Protocol) is the universal standard for AI tools:
- Created by Anthropic (Nov 2024)
- Adopted by OpenAI (March 2025)
- Supported by Google, LangChain, CrewAI, LlamaIndex
- Donated to Linux Foundation (Dec 2025)

**One MCP server = works with all frameworks.**

## Features

| Feature | Description |
|---------|-------------|
| **Natural Language** | Describe tools in plain English, get working code |
| **OpenAPI Import** | Auto-convert REST APIs with auth support |
| **Database CRUD** | Generate tools from SQLite/PostgreSQL schemas |
| **Multi-Provider** | Anthropic, OpenAI, Google Gemini support |
| **Web Search** | Research APIs before generating code |
| **Auth Injection** | Built-in API key management |
| **Health Checks** | Monitor server and auth status |
| **CI/CD Ready** | GitHub Actions workflows included |
| **Full Logging** | Complete execution traces |

## Quick Start

### Installation

```bash
pip install mcp-tool-factory
```

Install your preferred LLM provider:

```bash
# Anthropic Claude (recommended)
pip install mcp-tool-factory[anthropic]

# OpenAI GPT
pip install mcp-tool-factory[openai]

# Google Gemini
pip install mcp-tool-factory[google]

# All providers
pip install mcp-tool-factory[all-providers]
```

### Set Up API Key

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Choose one:
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
# OPENAI_API_KEY=sk-xxxxx
# GOOGLE_API_KEY=xxxxx
```

Get your API keys:
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/api-keys
- Google: https://aistudio.google.com/apikey

## Usage

### 1. Generate from Natural Language

```bash
# Basic generation
mcp-factory generate "Create a tool that fetches weather data for any city"

# With web search for API docs
mcp-factory generate "Stock price API using Alpha Vantage" --web-search

# With API key injection
mcp-factory generate "Weather API" --auth WEATHER_API_KEY --auth BACKUP_KEY

# Disable health check
mcp-factory generate "Simple calculator" --no-health-check

# Use specific provider
mcp-factory generate "Date utilities" --provider openai --model gpt-5.2
```

### 2. Generate from OpenAPI Specification

```bash
# Auto-detect base URL and auth from spec
mcp-factory from-openapi petstore.yaml

# Override base URL
mcp-factory from-openapi api.json --base-url https://api.example.com

# Custom server name
mcp-factory from-openapi spec.yaml --name MyAPIServer
```

**Supported Auth Types:**
- API Key (header, query, cookie)
- Bearer Token
- OAuth2
- Basic Auth

### 3. Generate from Database

```bash
# SQLite database
mcp-factory from-database ./myapp.db

# Specific tables only
mcp-factory from-database ./data.db --tables users --tables orders

# PostgreSQL
mcp-factory from-database "postgresql://user:pass@host/db" --type postgresql
```

**Generated CRUD Tools:**
- `get_<table>` - Get record by primary key
- `list_<table>` - List with filtering & pagination
- `create_<table>` - Insert new records
- `update_<table>` - Update existing records
- `delete_<table>` - Delete records

### 4. Test & Serve

```bash
# Run tests
mcp-factory test ./servers/my-server

# Start server for testing
mcp-factory serve ./servers/my-server

# With SSE transport
mcp-factory serve ./servers/my-server --transport sse --port 8080
```

## Generated Output

Each generation creates a complete server package:

```
servers/my-server/
├── server.py              # FastMCP server with all tools
├── tests/
│   ├── __init__.py
│   └── test_tools.py      # Pytest tests
├── .github/
│   └── workflows/
│       └── ci.yml         # GitHub Actions CI/CD
├── Dockerfile             # Container config with HEALTHCHECK
├── pyproject.toml         # Package configuration
├── README.md              # Usage documentation
├── skill.md               # Claude Code skill file
├── EXECUTION_LOG.md       # Full generation trace
└── execution_log.json     # Machine-readable log
```

## Use with AI Frameworks

### Claude Code / Claude Desktop

Add to `.claude/mcp.json`:
```json
{
  "mcpServers": {
    "my-tools": {
      "command": "python",
      "args": ["./servers/my-server/server.py"],
      "env": {
        "API_KEY": "your-api-key"
      }
    }
  }
}
```

### OpenAI Agents SDK

```python
from agents import Agent
from agents.mcp import MCPServerStdio

async with MCPServerStdio(
    command="python",
    args=["./servers/my-server/server.py"],
    env={"API_KEY": "your-key"}
) as mcp:
    agent = Agent(name="MyAgent", mcp_servers=[mcp])
```

### LangChain

```python
from langchain_mcp_adapters import load_mcp_tools

tools = await load_mcp_tools(
    command="python",
    args=["./servers/my-server/server.py"]
)
agent = create_react_agent(llm, tools)
```

### Google ADK

```python
from google.adk.tools import MCPToolAdapter

adapter = MCPToolAdapter(
    command="python",
    args=["./servers/my-server/server.py"]
)
agent = Agent(tools=[adapter])
```

## CLI Reference

```bash
# Natural language generation
mcp-factory generate "description" [OPTIONS]
  --output, -o      Output directory (default: ./servers)
  --name, -n        Server name
  --provider, -p    LLM provider: claude_code, anthropic, openai, google
  --model, -m       Model to use
  --web-search, -w  Search web for API docs first
  --auth, -a        Auth env vars (repeatable)
  --health-check    Include health check (default: enabled)

# OpenAPI generation
mcp-factory from-openapi OPENAPI_PATH [OPTIONS]
  --base-url, -u    API base URL (auto-detected if not set)
  --output, -o      Output directory
  --name, -n        Server name (auto-generated if not set)

# Database generation
mcp-factory from-database DATABASE_PATH [OPTIONS]
  --type, -t        Database type: sqlite, postgresql
  --output, -o      Output directory
  --name, -n        Server name
  --tables, -T      Specific tables (repeatable)

# Testing & serving
mcp-factory test SERVER_PATH
mcp-factory serve SERVER_PATH [--transport stdio|sse] [--port 8000]

# Info
mcp-factory info
```

## Configuration

### Supported Providers & Models

#### Anthropic Claude (recommended)
| Model ID | Description |
|----------|-------------|
| `claude-sonnet-4-5-20241022` | Sonnet 4.5 - Best for agents (default) |
| `claude-opus-4-5-20251101` | Opus 4.5 - Most intelligent |
| `claude-haiku-4-5-20241022` | Haiku 4.5 - Fastest |
| `claude-opus-4-20250514` | Opus 4 - Excellent coding |

#### OpenAI
| Model ID | Description |
|----------|-------------|
| `gpt-5.2` | GPT-5.2 - Latest flagship (default) |
| `gpt-5.1` | GPT-5.1 - Enhanced personalization |
| `gpt-4.1` | GPT-4.1 - 1M context, great coding |
| `o3` | o3 - Best reasoning |
| `o4-mini` | o4-mini - Fast reasoning |

#### Google Gemini
| Model ID | Description |
|----------|-------------|
| `gemini-3-flash` | Gemini 3 Flash (default) |
| `gemini-3-pro` | Gemini 3 Pro - Most capable |
| `gemini-2.5-flash` | Gemini 2.5 Flash - Best value |

### Programmatic Usage

```python
from tool_factory import ToolFactoryAgent
from tool_factory.config import FactoryConfig, LLMProvider

# Auto-detect provider from environment
agent = ToolFactoryAgent()

# Explicit configuration
config = FactoryConfig(
    provider=LLMProvider.ANTHROPIC,
    model="claude-sonnet-4-5-20241022",
    api_key="your-api-key",
)
agent = ToolFactoryAgent(config=config)

# Generate server
result = agent.generate_from_description_sync(
    description="Create a currency converter tool",
    server_name="CurrencyServer",
    web_search=True,
    auth_env_vars=["EXCHANGE_API_KEY"],
    include_health_check=True,
)

# Write to disk
result.write_to_directory("./servers/currency")
```

### OpenAPI Programmatic Usage

```python
import asyncio
import yaml

agent = ToolFactoryAgent()

with open("api.yaml") as f:
    spec = yaml.safe_load(f)

result = asyncio.run(agent.generate_from_openapi(
    openapi_spec=spec,
    base_url="https://api.example.com",  # Optional, auto-detected
    server_name="MyAPIServer",
))
```

### Database Programmatic Usage

```python
from tool_factory.database import (
    DatabaseType,
    DatabaseIntrospector,
    DatabaseServerGenerator,
)

# Introspect schema
introspector = DatabaseIntrospector(
    DatabaseType.SQLITE,
    "./myapp.db"
)
tables = introspector.get_tables()

# Generate server
generator = DatabaseServerGenerator(
    DatabaseType.SQLITE,
    "./myapp.db",
    tables=tables,
)
server_code = generator.generate_server_code("MyDBServer")
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MCP TOOL FACTORY                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────┐ │
│  │      INPUT       │   │    PROCESSING    │   │       OUTPUT         │ │
│  ├──────────────────┤   ├──────────────────┤   ├──────────────────────┤ │
│  │ • Natural Lang   │   │ • Web Search     │   │ • MCP Server         │ │
│  │ • OpenAPI Spec   │ → │ • LLM Generation │ → │ • Tests              │ │
│  │ • Database       │   │ • Code Gen       │   │ • Dockerfile         │ │
│  │                  │   │ • Validation     │   │ • CI/CD Workflow     │ │
│  └──────────────────┘   └──────────────────┘   │ • Documentation      │ │
│                                                 │ • Execution Log      │ │
│                                                 └──────────────────────┘ │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     LLM PROVIDERS                                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │   │
│  │  │ Anthropic│  │  OpenAI  │  │  Google  │  │ Claude Agent SDK │  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
              Works with ALL MCP-compatible frameworks
     ┌──────────┬──────────┬──────────┬──────────┬──────────┐
     │  Claude  │  OpenAI  │  Google  │ LangChain│  CrewAI  │
     │   Code   │  Agents  │   ADK    │          │          │
     └──────────┴──────────┴──────────┴──────────┴──────────┘
```

## Examples

### Weather API with Auth

```bash
mcp-factory generate "Weather API using OpenWeatherMap" \
  --web-search \
  --auth OPENWEATHER_API_KEY \
  --name WeatherServer
```

Generated `server.py` includes:
```python
# Auth configuration
AUTH_CONFIG = {
    "OPENWEATHER_API_KEY": os.environ.get("OPENWEATHER_API_KEY"),
}

@mcp.tool()
def health_check() -> dict:
    """Check server health and auth status."""
    return {
        "status": "healthy",
        "auth_config": {"OPENWEATHER_API_KEY": "configured"},
        ...
    }

@mcp.tool()
def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    api_key = require_auth("OPENWEATHER_API_KEY")
    ...
```

### REST API from OpenAPI

```bash
mcp-factory from-openapi petstore.yaml
```

Automatically generates tools for each endpoint with:
- Path parameter interpolation
- Query parameter handling
- Request body support
- Authentication headers
- Error handling

### Database CRUD

```bash
mcp-factory from-database ./ecommerce.db --tables products --tables orders
```

Generates complete CRUD operations:
```python
@mcp.tool()
def get_products(id: int) -> dict: ...

@mcp.tool()
def list_products(name: str = None, price: float = None, limit: int = 100) -> dict: ...

@mcp.tool()
def create_products(name: str, price: float, ...) -> dict: ...

@mcp.tool()
def update_products(id: int, name: str = None, price: float = None) -> dict: ...

@mcp.tool()
def delete_products(id: int) -> dict: ...
```

## Supported Frameworks

| Framework | Support | Integration |
|-----------|---------|-------------|
| Claude Code | Native | Built-in MCP client |
| Claude Desktop | Native | Built-in MCP client |
| OpenAI Agents SDK | Native | `mcp_servers` parameter |
| Google ADK | Native | MCP tool adapter |
| LangChain | Native | `langchain-mcp-adapters` |
| CrewAI | Native | MCP integration |
| LlamaIndex | Native | MCP tool spec |

## Development

```bash
# Clone and install
git clone https://github.com/HeshamFS/mcp-tool-factory
cd mcp-tool-factory
pip install -e ".[dev]"

# Run tests
pytest

# Type check
mypy src/

# Format
black src/
ruff check src/
```

## Project Structure

```
mcp-tool-factory/
├── src/tool_factory/
│   ├── __init__.py
│   ├── agent.py              # Main ToolFactoryAgent
│   ├── cli.py                # CLI commands
│   ├── config.py             # Configuration & providers
│   ├── models.py             # Data models
│   ├── prompts.py            # LLM prompts
│   ├── openapi.py            # OpenAPI parser & validator
│   ├── database.py           # Database introspection & CRUD
│   ├── web_search.py         # Web search integration
│   ├── execution_logger.py   # Full execution logging
│   ├── production.py         # Rate limiting, metrics
│   ├── validation.py         # Generated code validation
│   ├── auth/                 # OAuth2/PKCE authentication
│   │   ├── oauth2.py
│   │   ├── pkce.py
│   │   └── providers.py
│   ├── generators/
│   │   ├── server.py         # Server code generator
│   │   ├── docs.py           # Documentation generator
│   │   └── tests.py          # Test generation
│   ├── middleware/
│   │   └── validation.py     # Request/response validation
│   ├── observability/
│   │   └── telemetry.py      # OpenTelemetry integration
│   ├── providers/            # LLM provider implementations
│   │   ├── anthropic.py
│   │   ├── openai.py
│   │   ├── google.py
│   │   └── claude_code.py
│   ├── security/
│   │   └── scanner.py        # Security vulnerability scanning
│   ├── utils/
│   │   ├── input_validation.py
│   │   └── dependencies.py   # Package versioning
│   └── templates/
│       └── server.py.jinja
├── tests/                    # 498 tests
├── servers/                  # Generated servers
├── pyproject.toml
├── .env.example
└── README.md
```

## Production Features

### OAuth2/PKCE Authentication

Generate servers with OAuth2 authentication support:

```python
from tool_factory.auth import OAuth2Config, PKCECodeVerifier

# Configure OAuth2
config = OAuth2Config(
    client_id="your-client-id",
    authorization_url="https://example.com/oauth/authorize",
    token_url="https://example.com/oauth/token",
    scopes=["read", "write"],
    pkce_enabled=True,  # RFC 7636
)

# Generate PKCE verifier/challenge
verifier = PKCECodeVerifier.generate()
auth_url = config.get_authorization_url(
    code_challenge=verifier.challenge,
    code_challenge_method="S256",
)
```

### Rate Limiting

Built-in rate limiting with memory or Redis backends:

```python
from tool_factory.production import ProductionConfig, RateLimitBackend

config = ProductionConfig(
    rate_limit_enabled=True,
    rate_limit_requests=100,
    rate_limit_window_seconds=60,
    rate_limit_backend=RateLimitBackend.REDIS,  # or MEMORY
    redis_url="redis://localhost:6379",
)
```

### OpenTelemetry Integration

Tracing and metrics for production servers:

```python
from tool_factory.observability import TelemetryConfig, TelemetryExporter

config = TelemetryConfig(
    enabled=True,
    service_name="my-mcp-server",
    exporter_type=TelemetryExporter.OTLP,  # OTLP, Jaeger, Zipkin, Azure
    endpoint="http://localhost:4317",
)
```

### Security Scanning

Scan generated code for vulnerabilities:

```python
from tool_factory.security import scan_code, scan_file

# Scan code string
issues = scan_code('password = "hardcoded123"')

# Scan file
issues = scan_file("./servers/my-server/server.py")

for issue in issues:
    print(f"[{issue.severity}] {issue.message}")
```

Detected issues include:
- Hardcoded credentials
- SQL injection patterns
- Command injection (eval, exec, os.system)
- Insecure cryptography (MD5, SHA-1)
- Unsafe deserialization (pickle, yaml.load)
- SSL verification disabled

### Input Validation

Standardized validation utilities for generated servers:

```python
from tool_factory.utils import (
    validate_string,
    validate_email,
    validate_url,
    validate_finite,
    sanitize_string,
)

# Validate inputs
result = validate_email(user_input, "email")
if not result.is_valid:
    raise ValueError(result.error)

# Sanitize against XSS
safe_text = sanitize_string(user_input)
```

## Troubleshooting

### Common Errors

#### API Key Not Found
```
Error: ANTHROPIC_API_KEY not set
```
**Solution**: Set your API key in `.env` or environment:
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

#### Rate Limit Exceeded
```
Error: Rate limit exceeded. Retry after 60 seconds.
```
**Solution**:
- Wait for the rate limit window to reset
- Use Redis backend for distributed rate limiting
- Reduce request frequency

#### Generated Server Syntax Error
```
SyntaxError: invalid syntax in server.py
```
**Solution**:
- Check for missing imports in the generated code
- Run `python -m py_compile server.py` to validate syntax
- Report issue with the tool description that caused it

#### OpenAPI Validation Failed
```
Error: OpenAPI spec validation failed: missing required field 'paths'
```
**Solution**:
- Ensure your OpenAPI spec has all required fields (openapi, info, paths)
- Use OpenAPI 3.0+ format
- Validate with `openapi-spec-validator` before importing

#### Database Connection Failed
```
Error: Could not connect to database
```
**Solution**:
- Verify database path/URL is correct
- Check file permissions for SQLite
- Ensure PostgreSQL is running and accessible

### Provider-Specific Issues

#### Anthropic
| Issue | Solution |
|-------|----------|
| `invalid_api_key` | Verify key starts with `sk-ant-api03-` |
| `overloaded_error` | Retry with exponential backoff |
| `context_length_exceeded` | Reduce input size or use a larger model |

#### OpenAI
| Issue | Solution |
|-------|----------|
| `invalid_api_key` | Verify key starts with `sk-` |
| `rate_limit_exceeded` | Wait or upgrade API tier |
| `model_not_found` | Check model name (e.g., `gpt-4`, not `gpt4`) |

#### Google
| Issue | Solution |
|-------|----------|
| `PERMISSION_DENIED` | Enable Generative AI API in Google Cloud |
| `INVALID_ARGUMENT` | Check model name format |
| `RESOURCE_EXHAUSTED` | Wait for quota reset |

### Rate Limiting Best Practices

1. **Single Instance**: Use memory backend (default)
2. **Multiple Instances**: Use Redis backend
3. **Recommended Limits**:
   - Development: 100 requests/minute
   - Production: 1000 requests/minute with Redis

```python
from tool_factory.production import ProductionConfig, RateLimitBackend

# For production with multiple instances
config = ProductionConfig(
    rate_limit_enabled=True,
    rate_limit_backend=RateLimitBackend.REDIS,
    redis_url="redis://localhost:6379",
)
```

## Changelog

### v0.3.0 (Current)
- **OAuth2/PKCE Authentication**: Full OAuth2 flow with PKCE support (RFC 7636)
- **Rate Limiting**: Memory and Redis-backed rate limiting with sliding window
- **OpenTelemetry**: Tracing and metrics with multiple exporters (OTLP, Jaeger, Zipkin, Azure)
- **Security Scanning**: Detect vulnerabilities in generated code
- **Input Validation**: Standardized validation utilities
- **Request/Response Validation**: JSON Schema validation middleware
- **Provider Architecture**: Refactored LLM providers into separate modules
- **Dependency Versioning**: Realistic version constraints for all packages
- **Enhanced Test Generation**: Functional tests with mocking support
- **498 tests** with 68% code coverage

### v0.2.0
- Added `from-database` command for SQLite/PostgreSQL CRUD generation
- Enhanced OpenAPI support with auth (API Key, Bearer, OAuth2, Basic)
- Added `--auth` flag for API key injection
- Added health check endpoints to all generated servers
- Added GitHub Actions CI/CD workflow generation
- Auto-detect base URL and auth from OpenAPI specs
- Improved execution logging with full raw data

### v0.1.0
- Initial release
- Natural language to MCP server generation
- Basic OpenAPI support
- Multi-provider LLM support (Anthropic, OpenAI, Google)
- Web search for API documentation

## License

MIT

## Links

- GitHub: https://github.com/HeshamFS/mcp-tool-factory
- MCP Specification: https://modelcontextprotocol.io
- FastMCP: https://github.com/jlowin/fastmcp
