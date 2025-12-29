# Architecture

This document describes the internal architecture of MCP Tool Factory, its components, and how they interact.

## Overview

MCP Tool Factory is a code generation system that uses LLMs to create MCP (Model Context Protocol) servers from various inputs.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MCP Tool Factory                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │   CLI    │  │  Python  │  │   MCP    │  │   API    │  Interfaces │
│  │Interface │  │   API    │  │  Server  │  │ Endpoint │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       │             │             │             │                     │
│       └─────────────┴─────────────┴─────────────┘                     │
│                           │                                           │
│                    ┌──────┴──────┐                                   │
│                    │    Agent    │  Core Orchestration                │
│                    │ (Workflow)  │                                   │
│                    └──────┬──────┘                                   │
│                           │                                           │
│       ┌───────────────────┼───────────────────┐                      │
│       │                   │                   │                      │
│  ┌────┴────┐        ┌─────┴─────┐       ┌─────┴─────┐               │
│  │Providers│        │ Generators │       │  Parsers  │  Core Modules│
│  │(LLM API)│        │(Code Gen)  │       │(Input)    │               │
│  └─────────┘        └───────────┘       └───────────┘               │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. ToolFactoryAgent

The main orchestrator that coordinates the generation workflow.

**Location:** `src/tool_factory/agent.py`

**Responsibilities:**
- Accept generation requests from CLI/API
- Coordinate with LLM providers
- Manage generation workflow
- Handle errors and retries
- Track execution logs

```python
class ToolFactoryAgent:
    """Main agent for generating MCP servers."""

    def __init__(self, config: FactoryConfig = None):
        self.config = config or get_default_config()
        self.execution_logger = ExecutionLogger()

    async def generate_from_description(
        self,
        description: str,
        **options
    ) -> GeneratedServer:
        """Generate server from natural language."""
        # 1. Optionally search web for API docs
        # 2. Build prompt for LLM
        # 3. Call LLM to generate tool specs
        # 4. Generate server code
        # 5. Generate tests, docs, config
        # 6. Validate generated code
        # 7. Return complete package
```

### 2. LLM Providers

Abstraction layer for different LLM backends.

**Location:** `src/tool_factory/providers/`

```
providers/
├── __init__.py       # Provider factory
├── base.py           # ProviderInterface ABC
├── anthropic.py      # Anthropic Claude
├── openai.py         # OpenAI GPT
├── google.py         # Google Gemini
└── claude_code.py    # Claude Code OAuth
```

**Interface:**

```python
class ProviderInterface(ABC):
    """Base interface for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate response from LLM."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name."""
        pass
```

### 3. Generators

Code generation modules for different output types.

**Location:** `src/tool_factory/generators/`

```
generators/
├── __init__.py
├── server.py         # server.py generation
├── tests.py          # Test file generation
└── docs.py           # README, skill.md generation
```

**ServerGenerator:**

```python
class ServerGenerator:
    """Generates MCP server code."""

    def generate_server_code(
        self,
        name: str,
        tool_specs: list[ToolSpec],
        auth_config: AuthConfig,
        production_config: ProductionConfig,
    ) -> str:
        """Generate complete server.py."""
        pass

    def generate_dockerfile(
        self,
        tool_specs: list[ToolSpec],
        env_vars: list[str],
    ) -> str:
        """Generate Dockerfile."""
        pass

    def generate_pyproject(
        self,
        name: str,
        tool_specs: list[ToolSpec],
    ) -> str:
        """Generate pyproject.toml."""
        pass
```

### 4. Parsers

Input parsers for different source types.

**Location:** `src/tool_factory/`

```python
# openapi.py - OpenAPI specification parser
class OpenAPIParser:
    def __init__(self, spec: dict):
        self.spec = spec

    def get_endpoints(self) -> list[Endpoint]:
        """Extract API endpoints."""
        pass

    def get_auth_config(self) -> AuthConfig:
        """Extract authentication configuration."""
        pass

# database.py - Database schema introspection
class DatabaseIntrospector:
    def __init__(self, db_type: DatabaseType, connection_string: str):
        pass

    def get_tables(self) -> list[TableSchema]:
        """Introspect database tables."""
        pass
```

---

## Data Flow

### Generation from Description

```
User Description
       │
       ▼
┌──────────────┐
│  CLI/API     │
└──────┬───────┘
       │
       ▼
┌──────────────┐    ┌──────────────┐
│    Agent     │◄───│  Web Search  │ (optional)
└──────┬───────┘    │   (tavily)   │
       │            └──────────────┘
       ▼
┌──────────────┐
│  Build Prompt│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ LLM Provider │
│  (Anthropic) │
└──────┬───────┘
       │
       ▼ (JSON response)
┌──────────────┐
│ Parse Tool   │
│   Specs      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Generators  │
│  (Code Gen)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Validation  │
│  (Syntax)    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Security    │
│   Scan       │
└──────┬───────┘
       │
       ▼
GeneratedServer
```

### Generation from OpenAPI

```
OpenAPI Spec (YAML/JSON)
       │
       ▼
┌──────────────┐
│ OpenAPI      │
│ Validator    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ OpenAPI      │
│ Parser       │
└──────┬───────┘
       │
       ├──► Endpoints
       ├──► Auth Config
       └──► Base URL
              │
              ▼
       ┌──────────────┐
       │  Generators  │
       └──────┬───────┘
              │
              ▼
       GeneratedServer
```

### Generation from Database

```
Database Connection
       │
       ▼
┌──────────────┐
│ Database     │
│ Introspector │
└──────┬───────┘
       │
       ▼ (Table schemas)
┌──────────────┐
│ CRUD         │
│ Generator    │
└──────┬───────┘
       │
       ▼
GeneratedServer
```

---

## Module Structure

```
src/tool_factory/
├── __init__.py           # Package exports
├── agent.py              # Main ToolFactoryAgent
├── cli.py                # Click CLI commands
├── config.py             # Configuration classes
├── models.py             # Data models (ToolSpec, etc.)
│
├── providers/            # LLM provider implementations
│   ├── __init__.py
│   ├── base.py
│   ├── anthropic.py
│   ├── openai.py
│   ├── google.py
│   └── claude_code.py
│
├── generators/           # Code generators
│   ├── __init__.py
│   ├── server.py
│   ├── tests.py
│   └── docs.py
│
├── auth/                 # Authentication support
│   ├── __init__.py
│   ├── oauth2.py
│   ├── pkce.py
│   └── providers/
│       ├── github.py
│       ├── google.py
│       └── azure.py
│
├── templates/            # Jinja2 templates
│   ├── server.py.jinja2
│   ├── dockerfile.jinja2
│   ├── test.py.jinja2
│   └── readme.md.jinja2
│
├── openapi.py           # OpenAPI parsing
├── database.py          # Database introspection
├── production.py        # Production features
├── security.py          # Security scanning
├── validation.py        # Code validation
└── execution_logger.py  # Execution tracing
```

---

## Key Classes

### GeneratedServer

Represents a complete generated MCP server package.

```python
@dataclass
class GeneratedServer:
    """Complete generated server package."""

    name: str
    server_code: str
    tool_specs: list[ToolSpec]
    test_code: str
    dockerfile: str
    readme: str
    skill_file: str
    pyproject_toml: str
    github_actions: str
    execution_log: ExecutionLogger

    def write_to_directory(self, path: str) -> None:
        """Write all files to directory."""
        pass
```

### ToolSpec

Specification for a single tool.

```python
@dataclass
class ToolSpec:
    """Specification for an MCP tool."""

    name: str
    description: str
    input_schema: dict  # JSON Schema
    dependencies: list[str]
    implementation: str  # Python code
```

### FactoryConfig

Configuration for the agent.

```python
@dataclass
class FactoryConfig:
    """Agent configuration."""

    provider: LLMProvider
    model: str | None
    api_key: str | None
    temperature: float = 0.7
    max_retries: int = 3
```

### ProductionConfig

Production features configuration.

```python
@dataclass
class ProductionConfig:
    """Production features configuration."""

    enable_logging: bool = True
    enable_metrics: bool = False
    enable_rate_limiting: bool = False
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    enable_retries: bool = True
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
```

---

## Extension Points

### Custom Providers

Implement `ProviderInterface` for new LLM backends:

```python
from tool_factory.providers.base import ProviderInterface

class MyCustomProvider(ProviderInterface):
    def __init__(self, api_key: str, model: str):
        self.client = MyAPIClient(api_key)
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        response = await self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.content

    def get_model_name(self) -> str:
        return self.model
```

### Custom Templates

Override Jinja2 templates for customized output:

```python
from tool_factory.generators.server import ServerGenerator

generator = ServerGenerator()
generator.template_dir = "./my-templates"

# Uses ./my-templates/server.py.jinja2
```

### Custom Validators

Add custom security patterns:

```python
from tool_factory.security import SecurityScanner

scanner = SecurityScanner()
scanner.add_pattern(
    name="custom_check",
    pattern=r"my_dangerous_function\(",
    severity="HIGH",
    message="Avoid using my_dangerous_function",
)

issues = scanner.scan(code)
```

---

## Execution Logging

Full traceability of generation process.

```python
class ExecutionLogger:
    """Logs complete execution trace."""

    def log_step(self, step: str, details: str):
        """Log a workflow step."""
        pass

    def log_llm_call(
        self,
        system_prompt: str,
        user_prompt: str,
        raw_response: str,
        tokens_in: int,
        tokens_out: int,
    ):
        """Log an LLM API call."""
        pass

    def to_markdown(self) -> str:
        """Export as markdown."""
        pass

    def to_json(self) -> str:
        """Export as JSON."""
        pass
```

**Output Files:**

- `EXECUTION_LOG.md` - Human-readable trace
- `execution_log.json` - Machine-readable trace

---

## Security Architecture

### Input Validation

All inputs are validated before processing:

```python
def validate_description(description: str) -> str:
    """Validate and sanitize description."""
    if len(description) > 10000:
        raise ValueError("Description too long")
    # Sanitize potentially harmful content
    return sanitize(description)
```

### Output Validation

Generated code is validated:

```python
def validate_generated_code(code: str) -> tuple[bool, str]:
    """Validate Python syntax."""
    try:
        compile(code, "<string>", "exec")
        return True, ""
    except SyntaxError as e:
        return False, str(e)
```

### Security Scanning

Post-generation security checks:

```python
def scan_for_issues(code: str) -> list[SecurityIssue]:
    """Scan for security vulnerabilities."""
    issues = []
    for pattern in SECURITY_PATTERNS:
        matches = pattern.regex.findall(code)
        for match in matches:
            issues.append(SecurityIssue(
                severity=pattern.severity,
                message=pattern.message,
            ))
    return issues
```

---

## Performance Considerations

### LLM Call Optimization

- Single LLM call for tool generation
- Structured output (JSON) for reliable parsing
- Temperature tuning for consistency

### Code Generation

- Template-based generation (fast)
- No runtime reflection
- Pre-compiled Jinja2 templates

### Caching

- Web search results cached
- Database schemas cached
- Template compilation cached

---

## Testing Architecture

```
tests/
├── conftest.py           # Shared fixtures
├── test_agent.py         # Agent tests
├── test_cli.py           # CLI tests
├── test_providers/       # Provider tests
│   ├── test_anthropic.py
│   ├── test_openai.py
│   └── test_google.py
├── test_generators/      # Generator tests
│   ├── test_server.py
│   └── test_docs.py
├── test_openapi.py       # OpenAPI tests
├── test_database.py      # Database tests
├── test_security.py      # Security scan tests
└── test_integration/     # End-to-end tests
```

### Testing Strategy

1. **Unit Tests** - Individual functions
2. **Integration Tests** - Module interactions
3. **E2E Tests** - Full generation workflow
4. **Mock Tests** - LLM responses mocked

---

## Deployment

### As CLI Tool

```bash
pip install mcp-tool-factory
mcp-factory generate "..."
```

### As Python Library

```python
from tool_factory import ToolFactoryAgent
agent = ToolFactoryAgent()
result = agent.generate_from_description_sync("...")
```

### As MCP Server

```json
{
  "mcpServers": {
    "tool-factory": {
      "command": "python",
      "args": ["-m", "tool_factory.server"]
    }
  }
}
```

---

## Future Architecture

### Planned Improvements

1. **Plugin System** - Custom generators, validators
2. **Template Marketplace** - Share templates
3. **Multi-Language** - TypeScript, Go output
4. **Distributed Generation** - Parallel LLM calls
5. **Semantic Caching** - Reuse similar generations
