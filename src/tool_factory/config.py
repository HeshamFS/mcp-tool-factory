"""Configuration for MCP Tool Factory."""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env file from current directory or parent directories
def _load_env() -> None:
    """Load environment variables from .env file."""
    # Try current directory first
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        return

    # Try to find .env in parent directories (up to 3 levels)
    for parent in [Path.cwd().parent, Path.cwd().parent.parent, Path.cwd().parent.parent.parent]:
        env_path = parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            return

    # Also try the package directory
    package_dir = Path(__file__).parent.parent.parent
    env_path = package_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)

# Load .env on module import
_load_env()


class LLMProvider(Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"  # Direct API with ANTHROPIC_API_KEY
    CLAUDE_CODE = "claude_code"  # Claude Agent SDK with OAuth token (for Max/Pro subscribers)
    OPENAI = "openai"
    GOOGLE = "google"


# Available Claude models (as of Dec 2025)
# See: https://docs.anthropic.com/en/docs/about-claude/models
CLAUDE_MODELS = {
    # Claude 4.5 Series (Latest - Dec 2025)
    "claude-sonnet-4-5-20241022": "Claude Sonnet 4.5 - Best for agents & coding (recommended)",
    "claude-opus-4-5-20251101": "Claude Opus 4.5 - Most intelligent, released Nov 2025",
    "claude-haiku-4-5-20241022": "Claude Haiku 4.5 - Fastest, near-frontier performance",
    # Claude 4 Series (May 2025)
    "claude-sonnet-4-20250514": "Claude Sonnet 4 - Fast, intelligent",
    "claude-opus-4-20250514": "Claude Opus 4 - World's best coding model",
    # Legacy (being deprecated)
    "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet - Previous generation",
    "claude-3-5-haiku-20241022": "Claude 3.5 Haiku - Previous generation",
}

# Available OpenAI models (as of Dec 2025)
# See: https://platform.openai.com/docs/models
OPENAI_MODELS = {
    # GPT-5 Series (Latest - Dec 2025)
    "gpt-5.2": "GPT-5.2 - Latest flagship (Dec 2025)",
    "gpt-5.1": "GPT-5.1 - Enhanced personalization (Nov 2025)",
    "gpt-5": "GPT-5 - Flagship model",
    "gpt-5-mini": "GPT-5 Mini - Fast, efficient",
    "gpt-5-nano": "GPT-5 Nano - Ultra-fast",
    # GPT-4.1 Series (Oct 2025)
    "gpt-4.1": "GPT-4.1 - 1M context, excellent coding",
    "gpt-4.1-mini": "GPT-4.1 Mini - Fast, affordable",
    "gpt-4.1-nano": "GPT-4.1 Nano - Cheapest",
    # o-Series Reasoning Models
    "o3": "o3 - Most powerful reasoning model",
    "o3-mini": "o3-mini - Fast reasoning",
    "o4-mini": "o4-mini - Best cost-efficient reasoning",
    # GPT-4o Series (Previous generation)
    "gpt-4o": "GPT-4o - Fast multimodal",
    "gpt-4o-mini": "GPT-4o Mini - Budget-friendly",
}

# Available Google Gemini models (as of Dec 2025)
# See: https://ai.google.dev/gemini-api/docs/models
GOOGLE_MODELS = {
    # Gemini 2.0 Series (Latest stable)
    "gemini-2.0-flash": "Gemini 2.0 Flash - Fast & capable (recommended)",
    "gemini-2.0-flash-lite": "Gemini 2.0 Flash-Lite - Ultra-fast, cheap",
    # Gemini 1.5 Series (Stable)
    "gemini-1.5-flash": "Gemini 1.5 Flash - Fast, 1M context",
    "gemini-1.5-flash-8b": "Gemini 1.5 Flash-8B - Fastest",
    "gemini-1.5-pro": "Gemini 1.5 Pro - Most capable",
}

# Default models per provider
DEFAULT_MODELS = {
    LLMProvider.ANTHROPIC: "claude-sonnet-4-5-20241022",  # Claude Sonnet 4.5 - best for agents
    LLMProvider.CLAUDE_CODE: "claude-sonnet-4-5-20241022",  # Same model, OAuth auth
    LLMProvider.OPENAI: "gpt-5.2",  # GPT-5.2 - Latest flagship (Dec 2025)
    LLMProvider.GOOGLE: "gemini-2.0-flash",  # Gemini 2.0 Flash - fast & capable
}


@dataclass
class FactoryConfig:
    """Configuration for the Tool Factory.

    Attributes:
        provider: LLM provider to use (anthropic or openai)
        model: Model ID to use for generation
        api_key: API key (defaults to env var based on provider)
        max_tokens: Maximum tokens for generation
        temperature: Sampling temperature (0-1)
    """
    provider: LLMProvider = LLMProvider.ANTHROPIC
    model: str | None = None
    api_key: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.0

    def __post_init__(self) -> None:
        """Set defaults based on provider."""
        if self.model is None:
            self.model = DEFAULT_MODELS[self.provider]

        if self.api_key is None:
            self.api_key = self._get_api_key_from_env()

    def _get_api_key_from_env(self) -> str | None:
        """Get API key from environment variable."""
        env_vars = {
            LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            LLMProvider.CLAUDE_CODE: "CLAUDE_CODE_OAUTH_TOKEN",
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.GOOGLE: "GOOGLE_API_KEY",
        }
        env_var = env_vars.get(self.provider)
        if env_var:
            return os.environ.get(env_var)
        return None

    def validate(self) -> list[str]:
        """Validate configuration. Returns list of errors."""
        errors = []

        if not self.api_key:
            env_var = "ANTHROPIC_API_KEY" if self.provider == LLMProvider.ANTHROPIC else "OPENAI_API_KEY"
            errors.append(f"API key not set. Set {env_var} environment variable or pass api_key parameter.")

        if self.provider == LLMProvider.ANTHROPIC and self.model not in CLAUDE_MODELS:
            errors.append(f"Unknown Claude model: {self.model}. Available: {list(CLAUDE_MODELS.keys())}")

        # Claude Code SDK uses same models but doesn't require strict validation
        if self.provider == LLMProvider.CLAUDE_CODE:
            pass  # Claude Code SDK handles model validation internally

        if self.provider == LLMProvider.OPENAI and self.model not in OPENAI_MODELS:
            errors.append(f"Unknown OpenAI model: {self.model}. Available: {list(OPENAI_MODELS.keys())}")

        if self.provider == LLMProvider.GOOGLE and self.model not in GOOGLE_MODELS:
            errors.append(f"Unknown Google model: {self.model}. Available: {list(GOOGLE_MODELS.keys())}")

        return errors


def get_default_config() -> FactoryConfig:
    """Get default configuration from environment."""
    # Check which API key is available
    # Prefer Claude Code OAuth token first (for Max/Pro subscribers)
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return FactoryConfig(provider=LLMProvider.CLAUDE_CODE)
    elif os.environ.get("ANTHROPIC_API_KEY"):
        return FactoryConfig(provider=LLMProvider.ANTHROPIC)
    elif os.environ.get("OPENAI_API_KEY"):
        return FactoryConfig(provider=LLMProvider.OPENAI)
    elif os.environ.get("GOOGLE_API_KEY"):
        return FactoryConfig(provider=LLMProvider.GOOGLE)
    else:
        # Default to Claude Code, will fail validation if no key
        return FactoryConfig(provider=LLMProvider.CLAUDE_CODE)
