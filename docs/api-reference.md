# API Reference

Complete Python API reference for MCP Tool Factory.

## Overview

MCP Tool Factory can be used programmatically for advanced use cases, CI/CD integration, and custom workflows.

```python
from tool_factory import ToolFactoryAgent
from tool_factory.config import FactoryConfig, LLMProvider
```

---

## ToolFactoryAgent

The main class for generating MCP servers.

### Constructor

```python
ToolFactoryAgent(config: FactoryConfig | None = None)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `FactoryConfig` | Auto-detect | Configuration for the agent |

**Example:**

```python
from tool_factory import ToolFactoryAgent
from tool_factory.config import FactoryConfig, LLMProvider

# Auto-detect provider from environment
agent = ToolFactoryAgent()

# Explicit configuration
config = FactoryConfig(
    provider=LLMProvider.ANTHROPIC,
    model="claude-sonnet-4-5-20241022",
    api_key="sk-ant-api03-xxxxx",
)
agent = ToolFactoryAgent(config=config)
```

### Methods

#### generate_from_description_sync

Generate an MCP server from a natural language description (synchronous).

```python
def generate_from_description_sync(
    self,
    description: str,
    server_name: str = "GeneratedToolServer",
    web_search: bool = False,
    auth_env_vars: list[str] | None = None,
    include_health_check: bool = True,
    production_config: ProductionConfig | None = None,
) -> GeneratedServer
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `description` | `str` | Required | Natural language description of tools |
| `server_name` | `str` | `"GeneratedToolServer"` | Name for the server |
| `web_search` | `bool` | `False` | Search web for API docs first |
| `auth_env_vars` | `list[str]` | `None` | Environment variables for auth |
| `include_health_check` | `bool` | `True` | Include health check endpoint |
| `production_config` | `ProductionConfig` | `None` | Production features config |

**Returns:** `GeneratedServer`

**Example:**

```python
result = agent.generate_from_description_sync(
    description="Create a weather API tool that fetches current conditions",
    server_name="WeatherServer",
    web_search=True,
    auth_env_vars=["WEATHER_API_KEY"],
    include_health_check=True,
)

# Write to disk
result.write_to_directory("./servers/weather")
```

#### generate_from_description

Generate an MCP server from a natural language description (async).

```python
async def generate_from_description(
    self,
    description: str,
    server_name: str = "GeneratedToolServer",
    web_search: bool = False,
    auth_env_vars: list[str] | None = None,
    include_health_check: bool = True,
    production_config: ProductionConfig | None = None,
) -> GeneratedServer
```

**Example:**

```python
import asyncio

async def main():
    agent = ToolFactoryAgent()
    result = await agent.generate_from_description(
        description="Stock price API",
        server_name="StockServer",
        web_search=True,
    )
    result.write_to_directory("./servers/stock")

asyncio.run(main())
```

#### generate_from_openapi

Generate an MCP server from an OpenAPI specification (async).

```python
async def generate_from_openapi(
    self,
    openapi_spec: dict,
    base_url: str | None = None,
    server_name: str | None = None,
) -> GeneratedServer
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `openapi_spec` | `dict` | Required | Parsed OpenAPI specification |
| `base_url` | `str` | Auto-detect | Base URL for API calls |
| `server_name` | `str` | Auto-generate | Name for the server |

**Example:**

```python
import asyncio
import yaml

async def main():
    agent = ToolFactoryAgent()

    with open("api.yaml") as f:
        spec = yaml.safe_load(f)

    result = await agent.generate_from_openapi(
        openapi_spec=spec,
        base_url="https://api.example.com/v2",
        server_name="MyAPIServer",
    )
    result.write_to_directory("./servers/myapi")

asyncio.run(main())
```

---

## GeneratedServer

Represents a generated MCP server with all its artifacts.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Server name |
| `server_code` | `str` | Generated server.py content |
| `tool_specs` | `list[ToolSpec]` | List of generated tools |
| `test_code` | `str` | Generated test file content |
| `dockerfile` | `str` | Dockerfile content |
| `readme` | `str` | README.md content |
| `skill_file` | `str` | skill.md content |
| `pyproject_toml` | `str` | pyproject.toml content |
| `github_actions` | `str` | CI/CD workflow content |
| `execution_log` | `ExecutionLogger` | Full execution trace |

### Methods

#### write_to_directory

Write all generated files to a directory.

```python
def write_to_directory(self, directory: str) -> None
```

**Example:**

```python
result.write_to_directory("./servers/my-server")
```

Creates:

```
my-server/
├── server.py
├── tests/
│   ├── __init__.py
│   └── test_tools.py
├── .github/workflows/ci.yml
├── Dockerfile
├── pyproject.toml
├── README.md
├── skill.md
├── EXECUTION_LOG.md
└── execution_log.json
```

---

## FactoryConfig

Configuration for the ToolFactoryAgent.

### Constructor

```python
FactoryConfig(
    provider: LLMProvider = LLMProvider.ANTHROPIC,
    model: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.7,
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `provider` | `LLMProvider` | `ANTHROPIC` | LLM provider to use |
| `model` | `str` | Provider default | Model ID |
| `api_key` | `str` | Environment variable | API key |
| `temperature` | `float` | `0.7` | Generation temperature |

**Example:**

```python
from tool_factory.config import FactoryConfig, LLMProvider

config = FactoryConfig(
    provider=LLMProvider.OPENAI,
    model="gpt-4.1",
    temperature=0.5,
)
```

### get_default_config

Get configuration auto-detected from environment.

```python
from tool_factory.config import get_default_config

config = get_default_config()
print(f"Using {config.provider.value} with {config.model}")
```

---

## LLMProvider

Enum of supported LLM providers.

```python
from tool_factory.config import LLMProvider

class LLMProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    CLAUDE_CODE = "claude_code"
```

---

## ProductionConfig

Configuration for production features.

### Constructor

```python
from tool_factory.production import ProductionConfig

ProductionConfig(
    enable_logging: bool = True,
    enable_metrics: bool = False,
    enable_rate_limiting: bool = False,
    rate_limit_requests: int = 100,
    rate_limit_window_seconds: int = 60,
    enable_retries: bool = True,
    max_retries: int = 3,
    retry_delay_seconds: float = 1.0,
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_logging` | `bool` | `True` | Include structured logging |
| `enable_metrics` | `bool` | `False` | Include Prometheus metrics |
| `enable_rate_limiting` | `bool` | `False` | Enable rate limiting |
| `rate_limit_requests` | `int` | `100` | Requests per window |
| `rate_limit_window_seconds` | `int` | `60` | Rate limit window |
| `enable_retries` | `bool` | `True` | Enable retry patterns |
| `max_retries` | `int` | `3` | Maximum retry attempts |
| `retry_delay_seconds` | `float` | `1.0` | Base retry delay |

**Example:**

```python
from tool_factory.production import ProductionConfig

prod_config = ProductionConfig(
    enable_logging=True,
    enable_metrics=True,
    enable_rate_limiting=True,
    rate_limit_requests=1000,
    rate_limit_window_seconds=60,
)

result = agent.generate_from_description_sync(
    description="Production API",
    production_config=prod_config,
)
```

---

## ToolSpec

Specification for a generated tool.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Tool function name |
| `description` | `str` | Tool description |
| `input_schema` | `dict` | JSON Schema for inputs |
| `dependencies` | `list[str]` | Required packages |

**Example:**

```python
for tool in result.tool_specs:
    print(f"Tool: {tool.name}")
    print(f"Description: {tool.description}")
    print(f"Parameters: {tool.input_schema}")
```

---

## Database Module

Generate CRUD tools from database schemas.

### DatabaseIntrospector

Introspect database schema.

```python
from tool_factory.database import DatabaseType, DatabaseIntrospector

introspector = DatabaseIntrospector(
    db_type=DatabaseType.SQLITE,
    connection_string="./myapp.db",
)

tables = introspector.get_tables()
for table in tables:
    print(f"Table: {table.name}")
    print(f"Columns: {[c.name for c in table.columns]}")
    print(f"Primary Key: {table.primary_key}")
```

### DatabaseServerGenerator

Generate server code from database.

```python
from tool_factory.database import DatabaseServerGenerator

generator = DatabaseServerGenerator(
    db_type=DatabaseType.SQLITE,
    connection_string="./myapp.db",
    tables=tables,
)

server_code = generator.generate_server_code("MyDBServer")
tool_specs = generator.get_tool_specs()
env_vars = generator.get_env_vars()
```

### DatabaseType

```python
from tool_factory.database import DatabaseType

class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
```

---

## OpenAPI Module

Parse and validate OpenAPI specifications.

### OpenAPIParser

```python
from tool_factory.openapi import OpenAPIParser

parser = OpenAPIParser(spec)

# Get API info
info = parser.get_info()
print(f"Title: {info['title']}")
print(f"Version: {info['version']}")

# Get servers
servers = parser.get_servers()
for server in servers:
    print(f"URL: {server['url']}")

# Get auth configuration
auth_config = parser.get_auth_config()
print(f"Auth Type: {auth_config.auth_type}")
print(f"Env Var: {auth_config.env_var_name}")

# Get endpoints
endpoints = parser.get_endpoints()
for endpoint in endpoints:
    print(f"{endpoint.method} {endpoint.path}")
```

### OpenAPIValidator

```python
from tool_factory.openapi import OpenAPIValidator

validator = OpenAPIValidator()
is_valid = validator.validate(spec)
errors = validator.get_errors()
```

---

## Security Module

Scan code for security vulnerabilities.

### scan_code

```python
from tool_factory.security import scan_code

code = '''
password = "hardcoded123"
eval(user_input)
'''

issues = scan_code(code)
for issue in issues:
    print(f"[{issue.severity}] Line {issue.line}: {issue.message}")
```

### scan_file

```python
from tool_factory.security import scan_file

issues = scan_file("./server.py")
```

### SecurityIssue

```python
@dataclass
class SecurityIssue:
    severity: str      # "HIGH", "MEDIUM", "LOW"
    message: str       # Description of the issue
    line: int         # Line number
    pattern: str      # Pattern that matched
```

---

## Validation Module

Validate generated code and tool specifications.

### validate_python_code

```python
from tool_factory.validation import validate_python_code

is_valid, error = validate_python_code(code_string)
if not is_valid:
    print(f"Syntax error: {error}")
```

### validate_tool_specs

```python
from tool_factory.validation import validate_tool_specs

specs = validate_tool_specs([
    {"name": "my_tool", "description": "A tool"},
])

for spec in specs:
    print(f"Valid: {spec.name}")
```

---

## Execution Logger

Track full execution traces.

### ExecutionLogger

```python
from tool_factory.execution_logger import ExecutionLogger

logger = ExecutionLogger(
    server_name="MyServer",
    provider="anthropic",
    model="claude-3",
)

# Log steps
logger.log_step("init", "Starting generation")
logger.log_step("generate", "Generating tools")

# Log LLM calls
logger.log_llm_call(
    system_prompt="You are helpful",
    user_prompt="Generate a tool",
    raw_response="Here is your tool...",
    tokens_in=100,
    tokens_out=50,
)

# Export
markdown = logger.to_markdown()
json_str = logger.to_json()
```

---

## Complete Example

```python
import asyncio
from tool_factory import ToolFactoryAgent
from tool_factory.config import FactoryConfig, LLMProvider
from tool_factory.production import ProductionConfig

async def main():
    # Configure agent
    config = FactoryConfig(
        provider=LLMProvider.ANTHROPIC,
        model="claude-sonnet-4-5-20241022",
    )

    # Configure production features
    prod_config = ProductionConfig(
        enable_logging=True,
        enable_metrics=True,
        enable_rate_limiting=True,
        rate_limit_requests=100,
    )

    # Create agent
    agent = ToolFactoryAgent(config=config)

    # Generate server
    result = await agent.generate_from_description(
        description="Create a comprehensive weather API with current conditions, forecasts, and alerts",
        server_name="WeatherServer",
        web_search=True,
        auth_env_vars=["WEATHER_API_KEY"],
        include_health_check=True,
        production_config=prod_config,
    )

    # Inspect results
    print(f"Generated {len(result.tool_specs)} tools:")
    for tool in result.tool_specs:
        print(f"  - {tool.name}: {tool.description}")

    # Write to disk
    result.write_to_directory("./servers/weather")

    print(f"\nServer written to ./servers/weather")
    print(f"Run with: python ./servers/weather/server.py")

if __name__ == "__main__":
    asyncio.run(main())
```
