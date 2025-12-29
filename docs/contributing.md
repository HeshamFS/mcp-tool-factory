# Contributing

Thank you for your interest in contributing to MCP Tool Factory! This guide covers development setup, coding standards, and the contribution process.

## Overview

| Topic | Description |
|-------|-------------|
| [Development Setup](#development-setup) | Clone, install, configure |
| [Code Structure](#code-structure) | Project organization |
| [Coding Standards](#coding-standards) | Style, typing, documentation |
| [Testing](#testing) | Running and writing tests |
| [Pull Requests](#pull-requests) | Contribution workflow |

---

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- API key for at least one LLM provider (Anthropic recommended)

### Clone and Install

```bash
# Clone repository
git clone https://github.com/your-org/mcp-tool-factory
cd mcp-tool-factory

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate   # Windows

# Install in development mode with all extras
pip install -e ".[dev,all]"

# Or with uv (faster)
uv pip install -e ".[dev,all]"
```

### Configure API Keys

```bash
# Create .env file (not committed)
cat > .env << EOF
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
OPENAI_API_KEY=sk-xxxxx
GOOGLE_API_KEY=xxxxx
EOF

# Load environment
source .env
```

### Verify Setup

```bash
# Run tests
pytest

# Run CLI
mcp-factory info

# Run type checking
mypy src/

# Run linting
ruff check src/
```

---

## Code Structure

```
mcp-tool-factory/
├── src/tool_factory/       # Main package
│   ├── __init__.py         # Package exports
│   ├── agent.py            # Main ToolFactoryAgent
│   ├── cli.py              # Click CLI commands
│   ├── config.py           # Configuration classes
│   ├── models.py           # Data models
│   ├── providers/          # LLM providers
│   │   ├── base.py
│   │   ├── anthropic.py
│   │   ├── openai.py
│   │   └── google.py
│   ├── generators/         # Code generators
│   │   ├── server.py
│   │   ├── tests.py
│   │   └── docs.py
│   ├── auth/               # Authentication
│   ├── openapi.py          # OpenAPI parsing
│   ├── database.py         # Database introspection
│   ├── production.py       # Production features
│   ├── security.py         # Security scanning
│   └── validation.py       # Code validation
│
├── tests/                  # Test suite
│   ├── conftest.py         # Shared fixtures
│   ├── test_agent.py
│   ├── test_cli.py
│   └── ...
│
├── docs/                   # Documentation
│   ├── index.md
│   ├── getting-started.md
│   └── ...
│
├── examples/               # Example servers
├── pyproject.toml          # Project configuration
└── README.md
```

---

## Coding Standards

### Python Style

We follow PEP 8 with these specifics:

- **Line length:** 88 characters (Black default)
- **Quotes:** Double quotes for strings
- **Imports:** Sorted with isort

```python
# Good
from tool_factory.config import FactoryConfig, LLMProvider
from tool_factory.models import ToolSpec

def generate_server(name: str, specs: list[ToolSpec]) -> str:
    """Generate server code from tool specifications."""
    pass

# Bad
from tool_factory.config import FactoryConfig,LLMProvider
from tool_factory.models import *

def generate_server(name,specs):
    pass
```

### Type Hints

All functions must have complete type hints:

```python
from typing import Optional

def process_spec(
    spec: dict,
    validate: bool = True,
    timeout: float | None = None,
) -> tuple[ToolSpec, list[str]]:
    """Process a tool specification.

    Args:
        spec: Raw specification dictionary
        validate: Whether to validate the spec
        timeout: Optional timeout in seconds

    Returns:
        Tuple of (processed spec, list of warnings)

    Raises:
        ValueError: If spec is invalid
    """
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def generate_from_description(
    self,
    description: str,
    server_name: str = "GeneratedServer",
) -> GeneratedServer:
    """Generate an MCP server from a natural language description.

    This method uses an LLM to interpret the description and generate
    appropriate tool implementations.

    Args:
        description: Natural language description of desired tools.
            Can include multiple tools, authentication requirements,
            and API endpoints.
        server_name: Name for the generated server. Used in the
            server class name and output files.

    Returns:
        GeneratedServer containing all generated artifacts including
        server code, tests, Dockerfile, and documentation.

    Raises:
        ValueError: If description is empty or too long.
        ProviderError: If LLM call fails after retries.

    Example:
        >>> agent = ToolFactoryAgent()
        >>> result = agent.generate_from_description(
        ...     "Weather API with current conditions",
        ...     server_name="WeatherServer",
        ... )
        >>> result.write_to_directory("./output")
    """
    pass
```

### Error Handling

Never silently swallow errors:

```python
# Good
try:
    response = client.generate(prompt)
except APIError as e:
    logger.error(f"LLM call failed: {e}")
    raise ProviderError(f"Generation failed: {e}") from e

# Bad
try:
    response = client.generate(prompt)
except Exception:
    pass  # Never do this
```

### Logging

Use structured logging:

```python
import logging

logger = logging.getLogger(__name__)

def process_request(request_id: str, data: dict):
    logger.info(
        "Processing request",
        extra={"request_id": request_id, "data_size": len(data)},
    )
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tool_factory --cov-report=html

# Run specific test file
pytest tests/test_agent.py

# Run specific test
pytest tests/test_agent.py::TestAgent::test_generate

# Run with verbose output
pytest -v

# Run with debug output
pytest -s
```

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch

from tool_factory import ToolFactoryAgent
from tool_factory.config import FactoryConfig


class TestToolFactoryAgent:
    """Tests for ToolFactoryAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent with mocked provider."""
        config = FactoryConfig(provider="mock")
        return ToolFactoryAgent(config=config)

    @pytest.fixture
    def mock_llm_response(self):
        """Standard mock LLM response."""
        return {
            "tools": [
                {
                    "name": "test_tool",
                    "description": "A test tool",
                    "parameters": {},
                }
            ]
        }

    def test_generate_from_description(self, agent, mock_llm_response):
        """Test basic generation from description."""
        with patch.object(agent, "_call_llm", return_value=mock_llm_response):
            result = agent.generate_from_description_sync("Test description")

        assert result is not None
        assert len(result.tool_specs) == 1
        assert result.tool_specs[0].name == "test_tool"

    def test_generate_validates_input(self, agent):
        """Test that empty descriptions are rejected."""
        with pytest.raises(ValueError, match="Description cannot be empty"):
            agent.generate_from_description_sync("")

    def test_generate_handles_llm_error(self, agent):
        """Test graceful handling of LLM errors."""
        with patch.object(agent, "_call_llm", side_effect=Exception("API error")):
            with pytest.raises(ProviderError):
                agent.generate_from_description_sync("Test")
```

### Test Categories

```bash
# Unit tests (fast, no network)
pytest tests/unit/

# Integration tests (may use network)
pytest tests/integration/

# End-to-end tests (full workflow)
pytest tests/e2e/
```

### Coverage Requirements

- Minimum coverage: 85%
- All new code must have tests
- Critical paths must have multiple test cases

---

## Pull Requests

### Before Submitting

1. **Create an issue** for significant changes
2. **Fork and clone** the repository
3. **Create a branch** from `main`

```bash
git checkout -b feature/my-feature
```

### Development Workflow

```bash
# Make changes
# ...

# Run tests
pytest

# Run type checking
mypy src/

# Run linting
ruff check src/
ruff format src/

# Run security check
bandit -r src/

# Commit
git add .
git commit -m "feat: add new feature"
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add OAuth2/PKCE authentication support
fix: handle empty API responses gracefully
docs: update installation guide
test: add tests for OpenAPI parser
refactor: extract provider interface
chore: update dependencies
```

### Pull Request Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Coverage maintained/improved

## Checklist
- [ ] Code follows style guidelines
- [ ] Type hints complete
- [ ] Docstrings added/updated
- [ ] Documentation updated
- [ ] No security issues introduced
```

### Review Process

1. Automated checks must pass
2. At least one maintainer review
3. All comments addressed
4. Squash and merge

---

## Adding New Features

### Adding a New Provider

1. Create provider class:

```python
# src/tool_factory/providers/new_provider.py
from .base import ProviderInterface

class NewProvider(ProviderInterface):
    """New LLM provider implementation."""

    def __init__(self, api_key: str, model: str):
        self.client = NewAPIClient(api_key)
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

2. Register in factory:

```python
# src/tool_factory/providers/__init__.py
def get_provider(config: FactoryConfig) -> ProviderInterface:
    if config.provider == LLMProvider.NEW:
        from .new_provider import NewProvider
        return NewProvider(config.api_key, config.model)
```

3. Add tests:

```python
# tests/test_providers/test_new_provider.py
class TestNewProvider:
    def test_generate(self):
        # ...
```

4. Update documentation

### Adding a New Generator

1. Create generator class:

```python
# src/tool_factory/generators/new_generator.py
class NewGenerator:
    """Generate new artifact type."""

    def generate(self, specs: list[ToolSpec]) -> str:
        """Generate artifact from specs."""
        pass
```

2. Integrate with agent
3. Add tests
4. Update documentation

---

## Documentation

### Building Docs

```bash
# Install docs dependencies
pip install mkdocs mkdocs-material

# Serve locally
mkdocs serve

# Build
mkdocs build
```

### Documentation Standards

- All public APIs must be documented
- Include code examples
- Keep examples working and tested
- Use clear, concise language

---

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release PR
4. After merge, tag release
5. GitHub Actions publishes to PyPI

---

## Getting Help

- **Questions:** Open a Discussion
- **Bugs:** Open an Issue
- **Features:** Open an Issue first
- **Security:** Email maintainers directly

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow project guidelines

Thank you for contributing!
