# Getting Started

This guide will help you install MCP Tool Factory and generate your first MCP server.

## Prerequisites

- **Python 3.11+** - Required for running MCP Tool Factory
- **pip** - Python package manager
- **API Key** - From at least one LLM provider (Anthropic, OpenAI, or Google)

## Installation

### Basic Installation

```bash
pip install mcp-tool-factory
```

### Install with LLM Provider

Choose your preferred LLM provider:

```bash
# Anthropic Claude (recommended)
pip install mcp-tool-factory[anthropic]

# OpenAI GPT
pip install mcp-tool-factory[openai]

# Google Gemini
pip install mcp-tool-factory[google]

# All providers
pip install mcp-tool-factory[all-providers]

# Everything (all providers + dev tools)
pip install mcp-tool-factory[all]
```

### Development Installation

For contributing to MCP Tool Factory:

```bash
git clone https://github.com/hisham-maged/mcp-tool-factory
cd mcp-tool-factory
pip install -e ".[dev]"
```

## Configuration

### API Key Setup

Create a `.env` file in your project directory:

```bash
cp .env.example .env
```

Edit `.env` and add your API key:

```env
# Choose one provider:

# Anthropic (recommended)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# OpenAI
OPENAI_API_KEY=sk-xxxxx

# Google
GOOGLE_API_KEY=xxxxx
```

### Get API Keys

| Provider | Link | Key Format |
|----------|------|------------|
| Anthropic | [console.anthropic.com](https://console.anthropic.com/) | `sk-ant-api03-...` |
| OpenAI | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | `sk-...` |
| Google | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Alphanumeric |

### Verify Installation

```bash
# Check version
mcp-factory --version

# Show info
mcp-factory info
```

## Quick Start

### 1. Generate from Natural Language

The simplest way to create an MCP server:

```bash
mcp-factory generate "Create a tool that fetches weather data for any city"
```

This generates a complete server in `./servers/generatedtoolserver/`.

### 2. View Generated Files

```
servers/generatedtoolserver/
├── server.py              # FastMCP server with tools
├── tests/
│   └── test_tools.py      # Pytest tests
├── Dockerfile             # Container config
├── pyproject.toml         # Package config
├── README.md              # Documentation
├── skill.md               # Claude Code skill
└── .github/
    └── workflows/
        └── ci.yml         # CI/CD pipeline
```

### 3. Run Your Server

```bash
cd servers/generatedtoolserver
pip install -e .
python server.py
```

### 4. Test Your Server

```bash
mcp-factory test ./servers/generatedtoolserver
```

## Next Steps

### Add to Claude Code

Add your server to `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["./servers/generatedtoolserver/server.py"]
    }
  }
}
```

### Use with Other Frameworks

See the [Examples](examples.md) guide for integration with:

- OpenAI Agents SDK
- Google ADK
- LangChain
- CrewAI

### Advanced Features

- [CLI Reference](cli-reference.md) - All command options
- [OpenAPI Integration](openapi.md) - Import REST APIs
- [Database CRUD](database.md) - Generate from databases
- [Production Features](production.md) - Rate limiting, metrics

## Common First-Time Issues

### "ANTHROPIC_API_KEY not set"

**Solution**: Create `.env` file with your API key:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-api03-xxxxx" > .env
```

### "Module not found: anthropic"

**Solution**: Install with provider extras:

```bash
pip install mcp-tool-factory[anthropic]
```

### "Permission denied" when running server

**Solution**: Make server executable or use Python directly:

```bash
python ./servers/my-server/server.py
```

## Example: Weather API

Let's create a more sophisticated weather API:

```bash
# Generate with web search and API key injection
mcp-factory generate "Weather API using OpenWeatherMap with current weather and forecasts" \
  --web-search \
  --auth OPENWEATHER_API_KEY \
  --name WeatherServer
```

This generates:

```python
# server.py (excerpt)

@mcp.tool()
def get_current_weather(city: str, units: str = "metric") -> dict:
    """Get current weather for a city.

    Args:
        city: City name (e.g., "London", "New York")
        units: Temperature units - "metric" (Celsius) or "imperial" (Fahrenheit)

    Returns:
        Current weather data including temperature, humidity, conditions
    """
    api_key = require_auth("OPENWEATHER_API_KEY")
    response = httpx.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"q": city, "units": units, "appid": api_key}
    )
    return response.json()


@mcp.tool()
def get_forecast(city: str, days: int = 5) -> dict:
    """Get weather forecast for a city.

    Args:
        city: City name
        days: Number of days to forecast (1-5)

    Returns:
        Weather forecast data
    """
    ...
```

## Summary

You've learned how to:

1. Install MCP Tool Factory with your preferred LLM provider
2. Configure API keys
3. Generate your first MCP server
4. Run and test the server
5. Add it to Claude Code

Continue to the [CLI Reference](cli-reference.md) for complete command documentation.
