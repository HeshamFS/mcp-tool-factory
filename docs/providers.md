# LLM Providers

MCP Tool Factory supports multiple LLM providers for generating tool implementations. This guide covers configuration and best practices for each provider.

## Overview

| Provider | Best For | Default Model |
|----------|----------|---------------|
| **Anthropic** | Best overall quality, recommended | `claude-sonnet-4-5-20241022` |
| **OpenAI** | Fast generation, good coding | `gpt-5.2` |
| **Google** | Cost-effective, good quality | `gemini-2.0-flash` |
| **Claude Code** | Integration with Claude Code | Uses OAuth token |

## Provider Selection

### Automatic Detection

MCP Tool Factory automatically detects your provider based on environment variables:

```bash
# Checks in order:
# 1. ANTHROPIC_API_KEY
# 2. OPENAI_API_KEY
# 3. GOOGLE_API_KEY
# 4. CLAUDE_CODE_OAUTH_TOKEN
```

### Explicit Selection

#### CLI

```bash
mcp-factory generate "Weather API" --provider anthropic --model claude-sonnet-4-5-20241022
```

#### Python

```python
from tool_factory.config import FactoryConfig, LLMProvider

config = FactoryConfig(
    provider=LLMProvider.ANTHROPIC,
    model="claude-sonnet-4-5-20241022",
)
```

---

## Anthropic Claude

**Recommended** - Best code quality and tool understanding.

### Setup

```bash
# Install
pip install mcp-tool-factory[anthropic]

# Set API key
export ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

Get your key: [console.anthropic.com](https://console.anthropic.com/)

### Available Models

| Model ID | Description | Best For |
|----------|-------------|----------|
| `claude-sonnet-4-5-20241022` | Sonnet 4.5 - Best for agents | **Default**, most tasks |
| `claude-opus-4-5-20251101` | Opus 4.5 - Most intelligent | Complex, nuanced tasks |
| `claude-haiku-4-5-20241022` | Haiku 4.5 - Fastest | Quick, simple tasks |
| `claude-opus-4-20250514` | Opus 4 - Excellent coding | Code-heavy generation |
| `claude-sonnet-4-20250514` | Sonnet 4 - Balanced | General purpose |

### Usage

```bash
# Use default (Sonnet 4.5)
mcp-factory generate "Weather API" --provider anthropic

# Use specific model
mcp-factory generate "Complex financial tools" --provider anthropic --model claude-opus-4-5-20251101

# Fast generation
mcp-factory generate "Simple calculator" --provider anthropic --model claude-haiku-4-5-20241022
```

### Python API

```python
from tool_factory import ToolFactoryAgent
from tool_factory.config import FactoryConfig, LLMProvider

config = FactoryConfig(
    provider=LLMProvider.ANTHROPIC,
    model="claude-sonnet-4-5-20241022",
    api_key="sk-ant-api03-xxxxx",  # Optional, uses env var
    temperature=0.7,
)

agent = ToolFactoryAgent(config=config)
```

### Rate Limits

| Tier | Requests/min | Tokens/min |
|------|--------------|------------|
| Free | 5 | 20,000 |
| Build | 50 | 100,000 |
| Scale | 1,000 | 400,000 |

### Troubleshooting

| Error | Solution |
|-------|----------|
| `invalid_api_key` | Check key starts with `sk-ant-api03-` |
| `overloaded_error` | Wait and retry with backoff |
| `context_length_exceeded` | Use shorter descriptions |

---

## OpenAI GPT

Fast generation with excellent coding capabilities.

### Setup

```bash
# Install
pip install mcp-tool-factory[openai]

# Set API key
export OPENAI_API_KEY=sk-xxxxx
```

Get your key: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

### Available Models

| Model ID | Description | Best For |
|----------|-------------|----------|
| `gpt-5.2` | GPT-5.2 - Latest flagship | **Default**, complex tasks |
| `gpt-5.1` | GPT-5.1 - Enhanced personalization | Customized outputs |
| `gpt-4.1` | GPT-4.1 - 1M context | Large codebases |
| `o3` | o3 - Best reasoning | Complex logic |
| `o4-mini` | o4-mini - Fast reasoning | Quick analysis |

### Usage

```bash
# Use default (GPT-5.2)
mcp-factory generate "API tools" --provider openai

# Use specific model
mcp-factory generate "Complex analysis" --provider openai --model o3
```

### Python API

```python
from tool_factory.config import FactoryConfig, LLMProvider

config = FactoryConfig(
    provider=LLMProvider.OPENAI,
    model="gpt-5.2",
    temperature=0.7,
)
```

### Rate Limits

| Tier | RPM | TPM |
|------|-----|-----|
| Free | 3 | 40,000 |
| Tier 1 | 500 | 200,000 |
| Tier 2 | 5,000 | 2,000,000 |

### Troubleshooting

| Error | Solution |
|-------|----------|
| `invalid_api_key` | Check key starts with `sk-` |
| `rate_limit_exceeded` | Upgrade tier or wait |
| `model_not_found` | Check model name spelling |

---

## Google Gemini

Cost-effective with good generation quality.

### Setup

```bash
# Install
pip install mcp-tool-factory[google]

# Set API key
export GOOGLE_API_KEY=xxxxx
```

Get your key: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### Available Models

| Model ID | Description | Best For |
|----------|-------------|----------|
| `gemini-2.0-flash` | Gemini 2 Flash | **Default**, fast |
| `gemini-3-flash` | Gemini 3 Flash | Latest fast model |
| `gemini-3-pro` | Gemini 3 Pro | Most capable |
| `gemini-2.5-flash` | Gemini 2.5 Flash | Best value |

### Usage

```bash
# Use default
mcp-factory generate "Utility tools" --provider google

# Use specific model
mcp-factory generate "Complex API" --provider google --model gemini-3-pro
```

### Python API

```python
from tool_factory.config import FactoryConfig, LLMProvider

config = FactoryConfig(
    provider=LLMProvider.GOOGLE,
    model="gemini-2.0-flash",
)
```

### Rate Limits

| Tier | RPM | TPM |
|------|-----|-----|
| Free | 15 | 1,000,000 |
| Pay-as-you-go | 1,000 | 4,000,000 |

### Troubleshooting

| Error | Solution |
|-------|----------|
| `PERMISSION_DENIED` | Enable Generative AI API |
| `INVALID_ARGUMENT` | Check model name |
| `RESOURCE_EXHAUSTED` | Wait for quota reset |

---

## Claude Code OAuth

Use when running inside Claude Code with OAuth authentication.

### Setup

This provider is automatically used when running in Claude Code with an OAuth token.

```bash
export CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token
```

### Usage

```bash
mcp-factory generate "Tools" --provider claude_code
```

### Python API

```python
from tool_factory.config import FactoryConfig, LLMProvider

config = FactoryConfig(
    provider=LLMProvider.CLAUDE_CODE,
    api_key="oauth-token",
)
```

---

## Provider Comparison

### Quality

| Aspect | Anthropic | OpenAI | Google |
|--------|-----------|--------|--------|
| Code Quality | Excellent | Excellent | Good |
| Tool Understanding | Excellent | Good | Good |
| API Knowledge | Excellent | Good | Good |
| Error Handling | Excellent | Good | Good |

### Speed

| Provider | Fast Model | Standard Model |
|----------|------------|----------------|
| Anthropic | Haiku (~2s) | Sonnet (~5s) |
| OpenAI | o4-mini (~2s) | GPT-5.2 (~4s) |
| Google | Flash (~1s) | Pro (~3s) |

### Cost (per 1M tokens)

| Provider | Input | Output |
|----------|-------|--------|
| Anthropic Sonnet | $3.00 | $15.00 |
| OpenAI GPT-5.2 | $5.00 | $15.00 |
| Google Gemini 2 | $0.075 | $0.30 |

---

## Best Practices

### 1. Choose the Right Model

```bash
# Complex APIs - use most capable
mcp-factory generate "Financial trading API with risk management" \
  --provider anthropic --model claude-opus-4-5-20251101

# Simple utilities - use fast model
mcp-factory generate "Date formatter" \
  --provider anthropic --model claude-haiku-4-5-20241022
```

### 2. Handle Rate Limits

```python
from tool_factory import ToolFactoryAgent
import time

agent = ToolFactoryAgent()

for description in descriptions:
    try:
        result = agent.generate_from_description_sync(description)
    except Exception as e:
        if "rate_limit" in str(e).lower():
            time.sleep(60)
            result = agent.generate_from_description_sync(description)
```

### 3. Use Web Search for APIs

```bash
# Provider can research the API
mcp-factory generate "Stripe payment API" --web-search
```

### 4. Set Temperature Appropriately

```python
# Lower temperature for deterministic output
config = FactoryConfig(
    provider=LLMProvider.ANTHROPIC,
    temperature=0.3,  # More consistent
)

# Higher temperature for creative solutions
config = FactoryConfig(
    provider=LLMProvider.ANTHROPIC,
    temperature=0.9,  # More varied
)
```

---

## Environment Variables Reference

| Variable | Provider | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic | API key from console |
| `OPENAI_API_KEY` | OpenAI | API key from platform |
| `GOOGLE_API_KEY` | Google | API key from AI Studio |
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code | OAuth token |
| `MCP_FACTORY_PROVIDER` | All | Force provider selection |
| `MCP_FACTORY_MODEL` | All | Force model selection |
