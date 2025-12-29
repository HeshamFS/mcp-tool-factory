# MCP Tool Factory Documentation

Welcome to the MCP Tool Factory documentation. This comprehensive guide covers everything you need to know to generate production-ready MCP servers.

## What is MCP Tool Factory?

MCP Tool Factory is a powerful tool that generates universal MCP (Model Context Protocol) servers from:

- **Natural Language** - Describe your tools in plain English
- **OpenAPI Specifications** - Import existing REST APIs
- **Database Schemas** - Auto-generate CRUD operations

Generated servers work with **any** MCP-compatible AI framework: Claude, OpenAI Agents, Google ADK, LangChain, CrewAI, and more.

## Quick Navigation

### Getting Started

| Guide | Description |
|-------|-------------|
| [Installation](getting-started.md) | Install MCP Tool Factory and configure your environment |
| [Quick Start](getting-started.md#quick-start) | Generate your first MCP server in minutes |
| [Examples](examples.md) | Real-world usage examples |

### Core Features

| Guide | Description |
|-------|-------------|
| [CLI Reference](cli-reference.md) | Complete command-line interface documentation |
| [API Reference](api-reference.md) | Python programmatic API documentation |
| [Providers](providers.md) | Configure LLM providers (Anthropic, OpenAI, Google) |

### Input Sources

| Guide | Description |
|-------|-------------|
| [Natural Language](cli-reference.md#generate) | Generate from text descriptions |
| [OpenAPI](openapi.md) | Import REST APIs from OpenAPI specs |
| [Database](database.md) | Generate CRUD tools from databases |

### Production Features

| Guide | Description |
|-------|-------------|
| [Authentication](authentication.md) | OAuth2, PKCE, API keys, and more |
| [Production](production.md) | Rate limiting, metrics, telemetry |
| [Security](security.md) | Security scanning and best practices |

### Reference

| Guide | Description |
|-------|-------------|
| [Architecture](architecture.md) | System design and internals |
| [Troubleshooting](troubleshooting.md) | Common issues and solutions |
| [Contributing](contributing.md) | Development and contribution guide |

## Why MCP?

MCP (Model Context Protocol) is the universal standard for AI tools:

- **Created by Anthropic** (November 2024)
- **Adopted by OpenAI** (March 2025)
- **Supported by** Google, LangChain, CrewAI, LlamaIndex
- **Donated to Linux Foundation** (December 2025)

**One MCP server = works with all frameworks.**

## Feature Highlights

### Multi-Provider LLM Support

Generate tools using your preferred LLM provider:

```bash
# Anthropic Claude (recommended)
mcp-factory generate "Weather API" --provider anthropic

# OpenAI GPT
mcp-factory generate "Weather API" --provider openai

# Google Gemini
mcp-factory generate "Weather API" --provider google
```

### Web Search Integration

Research APIs before generating code:

```bash
mcp-factory generate "Stock prices using Alpha Vantage" --web-search
```

### Production-Ready Output

Every generated server includes:

- `server.py` - FastMCP server with all tools
- `tests/` - Pytest test suite
- `Dockerfile` - Container configuration with health checks
- `pyproject.toml` - Package configuration
- `.github/workflows/ci.yml` - CI/CD pipeline
- `README.md` - Usage documentation
- `EXECUTION_LOG.md` - Full generation trace

### Enterprise Features

- **OAuth2/PKCE Authentication** - Secure token flows
- **Rate Limiting** - Memory or Redis-backed
- **OpenTelemetry** - Distributed tracing
- **Security Scanning** - Vulnerability detection

## Supported Frameworks

| Framework | Status | Integration |
|-----------|--------|-------------|
| Claude Code | Native | Built-in MCP client |
| Claude Desktop | Native | Built-in MCP client |
| OpenAI Agents SDK | Native | `mcp_servers` parameter |
| Google ADK | Native | MCP tool adapter |
| LangChain | Native | `langchain-mcp-adapters` |
| CrewAI | Native | MCP integration |
| LlamaIndex | Native | MCP tool spec |

## Project Stats

- **868 tests** with **85.89% code coverage**
- **4 LLM providers** supported
- **3 input sources** (natural language, OpenAPI, database)
- **Production-ready** with auth, rate limiting, and telemetry

## License

MIT License - see [LICENSE](https://github.com/hisham-maged/mcp-tool-factory/blob/main/LICENSE) for details.

## Links

- [GitHub Repository](https://github.com/hisham-maged/mcp-tool-factory)
- [MCP Specification](https://modelcontextprotocol.io)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [Report Issues](https://github.com/hisham-maged/mcp-tool-factory/issues)
