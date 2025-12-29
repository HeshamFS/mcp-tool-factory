"""Production utilities for generated MCP servers.

Includes:
- Structured logging with JSON output
- Prometheus metrics
- Rate limiting
- Retry patterns with exponential backoff
"""

from dataclasses import dataclass
from enum import Enum


class LogLevel(Enum):
    """Log levels for structured logging."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class RateLimitBackend(Enum):
    """Rate limiting backend options."""
    MEMORY = "memory"  # Single-instance only
    REDIS = "redis"    # Distributed, production-ready


@dataclass
class ProductionConfig:
    """Configuration for production features."""
    enable_logging: bool = True
    log_level: LogLevel = LogLevel.INFO
    log_json: bool = True

    enable_metrics: bool = False
    metrics_port: int = 9090

    enable_rate_limiting: bool = False
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    rate_limit_backend: RateLimitBackend = RateLimitBackend.MEMORY
    redis_url: str = "redis://localhost:6379"

    enable_retries: bool = True
    max_retries: int = 3
    retry_base_delay: float = 1.0


class ProductionCodeGenerator:
    """Generate production utility code for MCP servers."""

    def __init__(self, config: ProductionConfig | None = None) -> None:
        self.config = config or ProductionConfig()

    def generate_imports(self) -> str:
        """Generate import statements for production utilities."""
        imports = []

        if self.config.enable_logging:
            imports.extend([
                "import logging",
                "import json",
                "from datetime import datetime",
            ])

        if self.config.enable_metrics:
            imports.append("from prometheus_client import Counter, Histogram, start_http_server")

        if self.config.enable_rate_limiting:
            imports.extend([
                "import time",
                "from collections import defaultdict",
                "from threading import Lock",
            ])
            if self.config.rate_limit_backend == RateLimitBackend.REDIS:
                imports.append("# Redis is imported inside RedisRateLimiter to allow graceful fallback")

        if self.config.enable_retries:
            imports.extend([
                "import random",
                "from functools import wraps",
            ])

        return "\n".join(imports)

    def generate_logging_code(self) -> str:
        """Generate structured logging setup."""
        if not self.config.enable_logging:
            return ""

        log_level = self.config.log_level.value

        if self.config.log_json:
            return f'''
# ============== STRUCTURED LOGGING ==============

class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {{
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }}

        # Add extra fields
        if hasattr(record, "tool_name"):
            log_data["tool_name"] = record.tool_name
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "error"):
            log_data["error"] = record.error

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(level: str = "{log_level}") -> logging.Logger:
    """Setup structured JSON logging."""
    logger = logging.getLogger("mcp_server")
    logger.setLevel(getattr(logging, level))

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    return logger


logger = setup_logging()


def log_tool_call(tool_name: str, duration_ms: float, success: bool, error: str | None = None):
    """Log a tool call with structured data."""
    extra = {{"tool_name": tool_name, "duration_ms": round(duration_ms, 2)}}
    if error:
        extra["error"] = error
        logger.error(f"Tool {{tool_name}} failed", extra=extra)
    else:
        logger.info(f"Tool {{tool_name}} completed", extra=extra)

'''
        else:
            return f'''
# ============== LOGGING ==============

logging.basicConfig(
    level=logging.{log_level},
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mcp_server")


def log_tool_call(tool_name: str, duration_ms: float, success: bool, error: str | None = None):
    """Log a tool call."""
    if error:
        logger.error(f"Tool {{tool_name}} failed after {{duration_ms:.2f}}ms: {{error}}")
    else:
        logger.info(f"Tool {{tool_name}} completed in {{duration_ms:.2f}}ms")

'''

    def generate_metrics_code(self) -> str:
        """Generate Prometheus metrics code."""
        if not self.config.enable_metrics:
            return ""

        return f'''
# ============== PROMETHEUS METRICS ==============

# Metrics
TOOL_CALLS = Counter(
    "mcp_tool_calls_total",
    "Total number of tool calls",
    ["tool_name", "status"]
)

TOOL_DURATION = Histogram(
    "mcp_tool_duration_seconds",
    "Tool call duration in seconds",
    ["tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

TOOL_ERRORS = Counter(
    "mcp_tool_errors_total",
    "Total number of tool errors",
    ["tool_name", "error_type"]
)


def start_metrics_server(port: int = {self.config.metrics_port}):
    """Start Prometheus metrics HTTP server."""
    start_http_server(port)
    logger.info(f"Metrics server started on port {{port}}")


def record_tool_metrics(tool_name: str, duration_seconds: float, success: bool, error_type: str | None = None):
    """Record metrics for a tool call."""
    status = "success" if success else "error"
    TOOL_CALLS.labels(tool_name=tool_name, status=status).inc()
    TOOL_DURATION.labels(tool_name=tool_name).observe(duration_seconds)

    if not success and error_type:
        TOOL_ERRORS.labels(tool_name=tool_name, error_type=error_type).inc()

'''

    def generate_rate_limiting_code(self) -> str:
        """Generate rate limiting code."""
        if not self.config.enable_rate_limiting:
            return ""

        # Generate base rate limiter interface
        base_code = '''
# ============== RATE LIMITING ==============

from abc import ABC, abstractmethod


class BaseRateLimiter(ABC):
    """Abstract base class for rate limiters."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    @abstractmethod
    def is_allowed(self, key: str = "default") -> bool:
        """Check if request is allowed under rate limit."""
        pass

    @abstractmethod
    def get_remaining(self, key: str = "default") -> int:
        """Get remaining requests in current window."""
        pass

    @abstractmethod
    def get_reset_time(self, key: str = "default") -> float:
        """Get seconds until rate limit resets."""
        pass

'''

        # In-memory implementation
        memory_code = f'''
class MemoryRateLimiter(BaseRateLimiter):
    """In-memory rate limiter using sliding window.

    NOTE: This only works for single-instance deployments.
    For distributed systems, use RedisRateLimiter instead.
    """

    def __init__(self, max_requests: int = {self.config.rate_limit_requests}, window_seconds: int = {self.config.rate_limit_window_seconds}):
        super().__init__(max_requests, window_seconds)
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, key: str = "default") -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        window_start = now - self.window_seconds

        with self.lock:
            # Clean old requests
            self.requests[key] = [t for t in self.requests[key] if t > window_start]

            # Check limit
            if len(self.requests[key]) >= self.max_requests:
                return False

            # Record request
            self.requests[key].append(now)
            return True

    def get_remaining(self, key: str = "default") -> int:
        """Get remaining requests in current window."""
        now = time.time()
        window_start = now - self.window_seconds

        with self.lock:
            self.requests[key] = [t for t in self.requests[key] if t > window_start]
            return max(0, self.max_requests - len(self.requests[key]))

    def get_reset_time(self, key: str = "default") -> float:
        """Get seconds until rate limit resets."""
        if not self.requests[key]:
            return 0

        oldest = min(self.requests[key])
        return max(0, oldest + self.window_seconds - time.time())

'''

        # Redis implementation (only if backend is Redis)
        if self.config.rate_limit_backend == RateLimitBackend.REDIS:
            redis_code = f'''
class RedisRateLimiter(BaseRateLimiter):
    """Redis-backed rate limiter for distributed deployments.

    Uses sliding window log algorithm with Redis sorted sets.
    Supports multiple server instances sharing rate limit state.
    """

    def __init__(
        self,
        max_requests: int = {self.config.rate_limit_requests},
        window_seconds: int = {self.config.rate_limit_window_seconds},
        redis_url: str = "{self.config.redis_url}",
        key_prefix: str = "ratelimit:",
    ):
        super().__init__(max_requests, window_seconds)
        import redis
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.key_prefix = key_prefix

    def _get_redis_key(self, key: str) -> str:
        return f"{{self.key_prefix}}{{key}}"

    def is_allowed(self, key: str = "default") -> bool:
        """Check if request is allowed using Redis sliding window."""
        import uuid
        redis_key = self._get_redis_key(key)
        now = time.time()
        window_start = now - self.window_seconds

        # Use pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(redis_key, 0, window_start)

        # Count current entries
        pipe.zcard(redis_key)

        # Execute pipeline
        results = pipe.execute()
        current_count = results[1]

        if current_count >= self.max_requests:
            return False

        # Add new request with unique member
        member = f"{{now}}:{{uuid.uuid4().hex[:8]}}"
        self.redis.zadd(redis_key, {{member: now}})
        self.redis.expire(redis_key, self.window_seconds + 1)

        return True

    def get_remaining(self, key: str = "default") -> int:
        """Get remaining requests from Redis."""
        redis_key = self._get_redis_key(key)
        now = time.time()
        window_start = now - self.window_seconds

        # Clean and count
        self.redis.zremrangebyscore(redis_key, 0, window_start)
        current_count = self.redis.zcard(redis_key)

        return max(0, self.max_requests - current_count)

    def get_reset_time(self, key: str = "default") -> float:
        """Get seconds until rate limit resets from Redis."""
        redis_key = self._get_redis_key(key)

        # Get oldest entry
        oldest = self.redis.zrange(redis_key, 0, 0, withscores=True)
        if not oldest:
            return 0

        oldest_time = oldest[0][1]
        return max(0, oldest_time + self.window_seconds - time.time())

'''
            # Factory function for Redis
            factory_code = f'''
def create_rate_limiter(
    backend: str = "redis",
    max_requests: int = {self.config.rate_limit_requests},
    window_seconds: int = {self.config.rate_limit_window_seconds},
    redis_url: str = "{self.config.redis_url}",
) -> BaseRateLimiter:
    """Create a rate limiter with the specified backend.

    Args:
        backend: "memory" for single-instance, "redis" for distributed
        max_requests: Maximum requests per window
        window_seconds: Window size in seconds
        redis_url: Redis connection URL (for redis backend)

    Returns:
        Rate limiter instance
    """
    if backend == "redis":
        return RedisRateLimiter(max_requests, window_seconds, redis_url)
    return MemoryRateLimiter(max_requests, window_seconds)


# Global rate limiter instance (using Redis)
rate_limiter = create_rate_limiter("redis")

'''
        else:
            redis_code = ""
            # Factory function for memory-only
            factory_code = f'''
def create_rate_limiter(
    backend: str = "memory",
    max_requests: int = {self.config.rate_limit_requests},
    window_seconds: int = {self.config.rate_limit_window_seconds},
    **kwargs,
) -> BaseRateLimiter:
    """Create a rate limiter with the specified backend.

    NOTE: Only memory backend is configured. For distributed deployments,
    enable Redis backend in production config.

    Args:
        backend: "memory" for single-instance
        max_requests: Maximum requests per window
        window_seconds: Window size in seconds

    Returns:
        Rate limiter instance
    """
    return MemoryRateLimiter(max_requests, window_seconds)


# Global rate limiter instance (in-memory, single-instance only)
rate_limiter = create_rate_limiter("memory")

'''

        # Common check function
        check_code = '''
def check_rate_limit(key: str = "default") -> dict | None:
    """Check rate limit and return error response if exceeded.

    Args:
        key: Rate limit key (e.g., user ID, IP address)

    Returns:
        None if allowed, error dict if rate limited
    """
    if not rate_limiter.is_allowed(key):
        return {
            "error": "Rate limit exceeded",
            "retry_after_seconds": round(rate_limiter.get_reset_time(key), 1),
            "remaining": rate_limiter.get_remaining(key),
            "limit": rate_limiter.max_requests,
            "window_seconds": rate_limiter.window_seconds,
        }
    return None


def get_rate_limit_headers(key: str = "default") -> dict[str, str]:
    """Get rate limit headers for HTTP responses.

    Args:
        key: Rate limit key

    Returns:
        Dict of rate limit headers
    """
    return {
        "X-RateLimit-Limit": str(rate_limiter.max_requests),
        "X-RateLimit-Remaining": str(rate_limiter.get_remaining(key)),
        "X-RateLimit-Reset": str(int(time.time() + rate_limiter.get_reset_time(key))),
    }

'''

        return base_code + memory_code + redis_code + factory_code + check_code

    def generate_retry_code(self) -> str:
        """Generate retry pattern code with exponential backoff."""
        if not self.config.enable_retries:
            return ""

        return f'''
# ============== RETRY PATTERNS ==============

class RetryError(Exception):
    """Raised when all retries are exhausted."""
    pass


def retry_with_backoff(
    max_retries: int = {self.config.max_retries},
    base_delay: float = {self.config.retry_base_delay},
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Decorator for retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to prevent thundering herd
        retryable_exceptions: Tuple of exceptions to retry on
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        break

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)

                    # Add jitter (0-25% of delay)
                    if jitter:
                        delay = delay * (1 + random.random() * 0.25)

                    logger.warning(
                        f"Retry {{attempt + 1}}/{{max_retries}} for {{func.__name__}} "
                        f"after {{delay:.2f}}s due to: {{e}}"
                    )
                    time.sleep(delay)

            raise RetryError(
                f"Failed after {{max_retries}} retries: {{last_exception}}"
            ) from last_exception

        return wrapper
    return decorator


async def async_retry_with_backoff(
    func,
    max_retries: int = {self.config.max_retries},
    base_delay: float = {self.config.retry_base_delay},
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Async retry with exponential backoff.

    Args:
        func: Async function to call
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Add random jitter
        retryable_exceptions: Tuple of exceptions to retry on

    Returns:
        Result of successful function call
    """
    import asyncio

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except retryable_exceptions as e:
            last_exception = e

            if attempt == max_retries:
                break

            delay = min(base_delay * (exponential_base ** attempt), max_delay)
            if jitter:
                delay = delay * (1 + random.random() * 0.25)

            logger.warning(
                f"Async retry {{attempt + 1}}/{{max_retries}} after {{delay:.2f}}s: {{e}}"
            )
            await asyncio.sleep(delay)

    raise RetryError(f"Failed after {{max_retries}} retries") from last_exception

'''

    def generate_all(self) -> str:
        """Generate all production utility code."""
        parts = [
            self.generate_imports(),
            "",
            self.generate_logging_code(),
            self.generate_metrics_code(),
            self.generate_rate_limiting_code(),
            self.generate_retry_code(),
        ]
        return "\n".join(part for part in parts if part)

    def generate_tool_wrapper(self) -> str:
        """Generate a wrapper function that applies all production features to a tool."""
        features = []

        if self.config.enable_rate_limiting:
            features.append("rate_limit_check")
        if self.config.enable_logging or self.config.enable_metrics:
            features.append("timing")
        if self.config.enable_retries:
            features.append("retry")

        if not features:
            return ""

        timing_code = ""
        if self.config.enable_logging or self.config.enable_metrics:
            timing_code = '''
    start_time = time.time()
    success = True
    error_msg = None'''

        rate_limit_code = ""
        if self.config.enable_rate_limiting:
            rate_limit_code = '''
    # Check rate limit
    rate_limit_error = check_rate_limit()
    if rate_limit_error:
        return rate_limit_error'''

        post_call_code = ""
        if self.config.enable_logging or self.config.enable_metrics:
            log_code = "log_tool_call(tool_name, duration_ms, success, error_msg)" if self.config.enable_logging else ""
            metrics_code = "record_tool_metrics(tool_name, duration_seconds, success, type(e).__name__ if error_msg else None)" if self.config.enable_metrics else ""

            post_call_code = f'''
    finally:
        duration_seconds = time.time() - start_time
        duration_ms = duration_seconds * 1000
        {log_code}
        {metrics_code}'''

        return f'''
# ============== TOOL WRAPPER ==============

def with_production_features(tool_name: str):
    """Decorator to add production features to a tool function."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            {timing_code}
            {rate_limit_code}

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            {post_call_code}

        return wrapper
    return decorator

'''


def generate_production_server_additions(config: ProductionConfig | None = None) -> str:
    """Generate production code to add to servers."""
    generator = ProductionCodeGenerator(config)
    return generator.generate_all() + generator.generate_tool_wrapper()
