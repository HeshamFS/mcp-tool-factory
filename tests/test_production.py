"""Tests for production utilities module."""

import pytest
from tool_factory.production import (
    LogLevel,
    RateLimitBackend,
    ProductionConfig,
    ProductionCodeGenerator,
    generate_production_server_additions,
)


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_log_levels_exist(self):
        """Test all log levels are defined."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"


class TestRateLimitBackend:
    """Tests for RateLimitBackend enum."""

    def test_rate_limit_backends_exist(self):
        """Test all rate limit backends are defined."""
        assert RateLimitBackend.MEMORY.value == "memory"
        assert RateLimitBackend.REDIS.value == "redis"


class TestProductionConfig:
    """Tests for ProductionConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ProductionConfig()

        assert config.enable_logging is True
        assert config.log_level == LogLevel.INFO
        assert config.log_json is True
        assert config.enable_metrics is False
        assert config.metrics_port == 9090
        assert config.enable_rate_limiting is False
        assert config.rate_limit_requests == 100
        assert config.rate_limit_window_seconds == 60
        assert config.rate_limit_backend == RateLimitBackend.MEMORY
        assert config.redis_url == "redis://localhost:6379"
        assert config.enable_retries is True
        assert config.max_retries == 3
        assert config.retry_base_delay == 1.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ProductionConfig(
            enable_logging=False,
            log_level=LogLevel.DEBUG,
            enable_metrics=True,
            metrics_port=8080,
            enable_rate_limiting=True,
            rate_limit_requests=50,
            rate_limit_backend=RateLimitBackend.REDIS,
            redis_url="redis://custom:6379",
            max_retries=5,
        )

        assert config.enable_logging is False
        assert config.log_level == LogLevel.DEBUG
        assert config.enable_metrics is True
        assert config.metrics_port == 8080
        assert config.enable_rate_limiting is True
        assert config.rate_limit_requests == 50
        assert config.rate_limit_backend == RateLimitBackend.REDIS
        assert config.redis_url == "redis://custom:6379"
        assert config.max_retries == 5


class TestProductionCodeGenerator:
    """Tests for ProductionCodeGenerator."""

    def test_default_generator(self):
        """Test generator with default config."""
        gen = ProductionCodeGenerator()
        assert gen.config.enable_logging is True

    def test_custom_config_generator(self):
        """Test generator with custom config."""
        config = ProductionConfig(enable_logging=False)
        gen = ProductionCodeGenerator(config)
        assert gen.config.enable_logging is False

    def test_generate_imports_logging_only(self):
        """Test import generation with only logging enabled."""
        config = ProductionConfig(
            enable_logging=True,
            enable_metrics=False,
            enable_rate_limiting=False,
            enable_retries=False,
        )
        gen = ProductionCodeGenerator(config)
        imports = gen.generate_imports()

        assert "import logging" in imports
        assert "import json" in imports
        assert "prometheus_client" not in imports
        assert "threading" not in imports
        assert "functools" not in imports

    def test_generate_imports_metrics(self):
        """Test import generation with metrics enabled."""
        config = ProductionConfig(
            enable_logging=False,
            enable_metrics=True,
            enable_rate_limiting=False,
            enable_retries=False,
        )
        gen = ProductionCodeGenerator(config)
        imports = gen.generate_imports()

        assert "prometheus_client" in imports
        assert "Counter" in imports
        assert "Histogram" in imports

    def test_generate_imports_rate_limiting(self):
        """Test import generation with rate limiting enabled."""
        config = ProductionConfig(
            enable_logging=False,
            enable_metrics=False,
            enable_rate_limiting=True,
            enable_retries=False,
        )
        gen = ProductionCodeGenerator(config)
        imports = gen.generate_imports()

        assert "import time" in imports
        assert "from collections import defaultdict" in imports
        assert "from threading import Lock" in imports

    def test_generate_imports_retries(self):
        """Test import generation with retries enabled."""
        config = ProductionConfig(
            enable_logging=False,
            enable_metrics=False,
            enable_rate_limiting=False,
            enable_retries=True,
        )
        gen = ProductionCodeGenerator(config)
        imports = gen.generate_imports()

        assert "import random" in imports
        assert "from functools import wraps" in imports

    def test_generate_logging_code_disabled(self):
        """Test no logging code when disabled."""
        config = ProductionConfig(enable_logging=False)
        gen = ProductionCodeGenerator(config)
        code = gen.generate_logging_code()

        assert code == ""

    def test_generate_logging_code_json(self):
        """Test JSON logging code generation."""
        config = ProductionConfig(enable_logging=True, log_json=True)
        gen = ProductionCodeGenerator(config)
        code = gen.generate_logging_code()

        assert "JSONFormatter" in code
        assert "class JSONFormatter" in code
        assert "json.dumps" in code
        assert "setup_logging" in code
        assert "log_tool_call" in code

    def test_generate_logging_code_plain(self):
        """Test plain logging code generation."""
        config = ProductionConfig(enable_logging=True, log_json=False)
        gen = ProductionCodeGenerator(config)
        code = gen.generate_logging_code()

        assert "JSONFormatter" not in code
        assert "basicConfig" in code
        assert "log_tool_call" in code

    def test_generate_logging_code_log_level(self):
        """Test log level is correctly set."""
        config = ProductionConfig(enable_logging=True, log_level=LogLevel.DEBUG)
        gen = ProductionCodeGenerator(config)
        code = gen.generate_logging_code()

        assert "DEBUG" in code

    def test_generate_metrics_code_disabled(self):
        """Test no metrics code when disabled."""
        config = ProductionConfig(enable_metrics=False)
        gen = ProductionCodeGenerator(config)
        code = gen.generate_metrics_code()

        assert code == ""

    def test_generate_metrics_code_enabled(self):
        """Test metrics code generation."""
        config = ProductionConfig(enable_metrics=True, metrics_port=9999)
        gen = ProductionCodeGenerator(config)
        code = gen.generate_metrics_code()

        assert "TOOL_CALLS = Counter" in code
        assert "TOOL_DURATION = Histogram" in code
        assert "TOOL_ERRORS = Counter" in code
        assert "start_metrics_server" in code
        assert "record_tool_metrics" in code
        assert "9999" in code

    def test_generate_rate_limiting_code_disabled(self):
        """Test no rate limiting code when disabled."""
        config = ProductionConfig(enable_rate_limiting=False)
        gen = ProductionCodeGenerator(config)
        code = gen.generate_rate_limiting_code()

        assert code == ""

    def test_generate_rate_limiting_code_memory_backend(self):
        """Test rate limiting code generation with memory backend."""
        config = ProductionConfig(
            enable_rate_limiting=True,
            rate_limit_requests=50,
            rate_limit_window_seconds=30,
            rate_limit_backend=RateLimitBackend.MEMORY,
        )
        gen = ProductionCodeGenerator(config)
        code = gen.generate_rate_limiting_code()

        assert "class BaseRateLimiter" in code
        assert "class MemoryRateLimiter" in code
        assert "is_allowed" in code
        assert "get_remaining" in code
        assert "get_reset_time" in code
        assert "check_rate_limit" in code
        assert "get_rate_limit_headers" in code
        assert "50" in code  # max_requests
        assert "30" in code  # window_seconds
        # Memory backend should NOT include Redis class definition
        assert "class RedisRateLimiter" not in code

    def test_generate_rate_limiting_code_redis_backend(self):
        """Test rate limiting code generation with Redis backend."""
        config = ProductionConfig(
            enable_rate_limiting=True,
            rate_limit_requests=100,
            rate_limit_window_seconds=60,
            rate_limit_backend=RateLimitBackend.REDIS,
            redis_url="redis://myredis:6379",
        )
        gen = ProductionCodeGenerator(config)
        code = gen.generate_rate_limiting_code()

        assert "class BaseRateLimiter" in code
        assert "class MemoryRateLimiter" in code
        assert "class RedisRateLimiter" in code
        assert "redis://myredis:6379" in code
        assert "zremrangebyscore" in code  # Redis sorted set operation
        assert "pipeline" in code  # Redis pipeline for atomicity
        assert "create_rate_limiter" in code
        assert 'backend: str = "redis"' in code

    def test_generate_retry_code_disabled(self):
        """Test no retry code when disabled."""
        config = ProductionConfig(enable_retries=False)
        gen = ProductionCodeGenerator(config)
        code = gen.generate_retry_code()

        assert code == ""

    def test_generate_retry_code_enabled(self):
        """Test retry code generation."""
        config = ProductionConfig(
            enable_retries=True,
            max_retries=5,
            retry_base_delay=2.0,
        )
        gen = ProductionCodeGenerator(config)
        code = gen.generate_retry_code()

        assert "class RetryError" in code
        assert "retry_with_backoff" in code
        assert "async_retry_with_backoff" in code
        assert "exponential_base" in code
        assert "jitter" in code
        assert "5" in code  # max_retries
        assert "2.0" in code  # base_delay

    def test_generate_all_nothing_enabled(self):
        """Test generate_all with nothing enabled."""
        config = ProductionConfig(
            enable_logging=False,
            enable_metrics=False,
            enable_rate_limiting=False,
            enable_retries=False,
        )
        gen = ProductionCodeGenerator(config)
        code = gen.generate_all()

        # Should be essentially empty
        assert len(code.strip()) == 0

    def test_generate_all_everything_enabled(self):
        """Test generate_all with everything enabled."""
        config = ProductionConfig(
            enable_logging=True,
            enable_metrics=True,
            enable_rate_limiting=True,
            enable_retries=True,
        )
        gen = ProductionCodeGenerator(config)
        code = gen.generate_all()

        assert "STRUCTURED LOGGING" in code
        assert "PROMETHEUS METRICS" in code
        assert "RATE LIMITING" in code
        assert "RETRY PATTERNS" in code

    def test_generate_tool_wrapper_nothing_enabled(self):
        """Test no tool wrapper when no features that need timing enabled."""
        config = ProductionConfig(
            enable_logging=False,
            enable_metrics=False,
            enable_rate_limiting=False,
            enable_retries=False,
        )
        gen = ProductionCodeGenerator(config)
        code = gen.generate_tool_wrapper()

        # Tool wrapper still generated but with minimal features
        # When nothing needs timing, wrapper is empty
        assert code == ""

    def test_generate_tool_wrapper_with_features(self):
        """Test tool wrapper generation with features."""
        config = ProductionConfig(
            enable_logging=True,
            enable_metrics=True,
            enable_rate_limiting=True,
        )
        gen = ProductionCodeGenerator(config)
        code = gen.generate_tool_wrapper()

        assert "with_production_features" in code
        assert "decorator" in code


class TestGenerateProductionServerAdditions:
    """Tests for the convenience function."""

    def test_with_default_config(self):
        """Test with default configuration."""
        code = generate_production_server_additions()

        # Default has logging and retries enabled
        assert "STRUCTURED LOGGING" in code
        assert "RETRY PATTERNS" in code

    def test_with_custom_config(self):
        """Test with custom configuration."""
        config = ProductionConfig(
            enable_logging=False,
            enable_metrics=True,
        )
        code = generate_production_server_additions(config)

        assert "STRUCTURED LOGGING" not in code
        assert "PROMETHEUS METRICS" in code
