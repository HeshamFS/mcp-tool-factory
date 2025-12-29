# Production Features

MCP Tool Factory generates production-ready servers with built-in support for logging, metrics, rate limiting, and retry patterns.

## Overview

Enable production features via CLI or Python API:

```bash
# CLI
mcp-factory generate "API tools" \
  --enable-logging \
  --enable-metrics \
  --enable-rate-limiting \
  --rate-limit 100 \
  --rate-window 60

# Python
from tool_factory.production import ProductionConfig
```

---

## Structured Logging

Enable comprehensive logging for debugging and monitoring.

### Configuration

```bash
mcp-factory generate "API" --enable-logging
```

```python
from tool_factory.production import ProductionConfig

config = ProductionConfig(
    enable_logging=True,
)
```

### Generated Code

```python
import logging
import json
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
)
logger = logging.getLogger(__name__)

class StructuredLogger:
    """JSON structured logger for production."""

    @staticmethod
    def log(level: str, message: str, **context):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **context,
        }
        print(json.dumps(log_entry))

    @staticmethod
    def info(message: str, **context):
        StructuredLogger.log("INFO", message, **context)

    @staticmethod
    def error(message: str, **context):
        StructuredLogger.log("ERROR", message, **context)

    @staticmethod
    def warning(message: str, **context):
        StructuredLogger.log("WARNING", message, **context)

# Usage in tools
@mcp.tool()
def get_weather(city: str) -> dict:
    """Get weather for a city."""
    StructuredLogger.info("Weather request", city=city)
    try:
        response = httpx.get(f"{BASE_URL}/weather", params={"city": city})
        StructuredLogger.info("Weather response", status=response.status_code)
        return response.json()
    except Exception as e:
        StructuredLogger.error("Weather request failed", error=str(e), city=city)
        raise
```

### Log Output

```json
{"timestamp": "2025-01-15T10:30:00.000000", "level": "INFO", "message": "Weather request", "city": "Seattle"}
{"timestamp": "2025-01-15T10:30:01.234567", "level": "INFO", "message": "Weather response", "status": 200}
```

### Log Aggregation

Logs are JSON-formatted for easy ingestion by:

- **Elasticsearch / Logstash / Kibana (ELK)**
- **Datadog**
- **Splunk**
- **CloudWatch Logs**
- **Google Cloud Logging**

---

## Prometheus Metrics

Export metrics for monitoring and alerting.

### Configuration

```bash
mcp-factory generate "API" --enable-metrics
```

```python
config = ProductionConfig(
    enable_metrics=True,
)
```

### Generated Code

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Define metrics
TOOL_CALLS = Counter(
    'mcp_tool_calls_total',
    'Total number of tool calls',
    ['tool_name', 'status']
)

TOOL_LATENCY = Histogram(
    'mcp_tool_latency_seconds',
    'Tool call latency in seconds',
    ['tool_name'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
)

TOOL_ERRORS = Counter(
    'mcp_tool_errors_total',
    'Total number of tool errors',
    ['tool_name', 'error_type']
)

ACTIVE_REQUESTS = Gauge(
    'mcp_active_requests',
    'Number of currently active requests'
)

# Decorator for automatic metrics
def with_metrics(tool_name: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ACTIVE_REQUESTS.inc()
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                TOOL_CALLS.labels(tool_name=tool_name, status="success").inc()
                return result
            except Exception as e:
                TOOL_CALLS.labels(tool_name=tool_name, status="error").inc()
                TOOL_ERRORS.labels(tool_name=tool_name, error_type=type(e).__name__).inc()
                raise
            finally:
                TOOL_LATENCY.labels(tool_name=tool_name).observe(time.time() - start_time)
                ACTIVE_REQUESTS.dec()
        return wrapper
    return decorator

# Usage
@mcp.tool()
@with_metrics("get_weather")
def get_weather(city: str) -> dict:
    """Get weather for a city."""
    # Implementation
```

### Metrics Endpoint

```python
@mcp.tool()
def get_metrics() -> str:
    """Get Prometheus metrics."""
    return generate_latest().decode('utf-8')
```

### Available Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `mcp_tool_calls_total` | Counter | tool_name, status | Total tool invocations |
| `mcp_tool_latency_seconds` | Histogram | tool_name | Request duration |
| `mcp_tool_errors_total` | Counter | tool_name, error_type | Error counts |
| `mcp_active_requests` | Gauge | - | Current active requests |

### Prometheus Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mcp-server'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Import the generated Grafana dashboard JSON for visualization.

---

## Rate Limiting

Protect your server from abuse with request rate limiting.

### Configuration

```bash
mcp-factory generate "API" \
  --enable-rate-limiting \
  --rate-limit 100 \
  --rate-window 60
```

```python
config = ProductionConfig(
    enable_rate_limiting=True,
    rate_limit_requests=100,     # Max requests
    rate_limit_window_seconds=60, # Per time window
)
```

### Generated Code

```python
import time
from collections import defaultdict
from threading import Lock

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, client_id: str = "default") -> bool:
        """Check if request is allowed for client."""
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            # Remove old requests
            self.requests[client_id] = [
                t for t in self.requests[client_id]
                if t > window_start
            ]

            # Check limit
            if len(self.requests[client_id]) >= self.max_requests:
                return False

            # Record request
            self.requests[client_id].append(now)
            return True

    def get_remaining(self, client_id: str = "default") -> int:
        """Get remaining requests for client."""
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            current = len([
                t for t in self.requests[client_id]
                if t > window_start
            ])
            return max(0, self.max_requests - current)

# Global rate limiter
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

def require_rate_limit(client_id: str = "default"):
    """Check rate limit before processing."""
    if not rate_limiter.is_allowed(client_id):
        remaining = rate_limiter.get_remaining(client_id)
        raise ValueError(
            f"Rate limit exceeded. {remaining} requests remaining. "
            f"Try again in {rate_limiter.window_seconds} seconds."
        )

# Usage
@mcp.tool()
def get_weather(city: str) -> dict:
    """Get weather for a city."""
    require_rate_limit()
    # Implementation
```

### Rate Limit Response

When limit exceeded:

```json
{
  "error": "Rate limit exceeded. 0 requests remaining. Try again in 60 seconds."
}
```

### Redis-Backed Rate Limiting

For distributed deployments:

```python
import redis

class RedisRateLimiter:
    """Redis-backed rate limiter for distributed systems."""

    def __init__(
        self,
        redis_url: str,
        max_requests: int = 100,
        window_seconds: int = 60
    ):
        self.redis = redis.from_url(redis_url)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_allowed(self, client_id: str = "default") -> bool:
        key = f"rate_limit:{client_id}"
        pipe = self.redis.pipeline()

        # Increment counter
        pipe.incr(key)
        pipe.expire(key, self.window_seconds)
        results = pipe.execute()

        count = results[0]
        return count <= self.max_requests
```

---

## Retry Patterns

Handle transient failures with automatic retries.

### Configuration

```python
config = ProductionConfig(
    enable_retries=True,
    max_retries=3,
    retry_delay_seconds=1.0,
)
```

### Generated Code

```python
import time
import random
from functools import wraps

class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True

def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: tuple = (Exception,),
):
    """Decorator for automatic retries with exponential backoff."""
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
                        raise

                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** attempt)
                    jitter = random.uniform(0, delay * 0.1)
                    time.sleep(delay + jitter)

                    StructuredLogger.warning(
                        "Retrying request",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(e),
                    )

            raise last_exception
        return wrapper
    return decorator

# Usage
@mcp.tool()
@with_retry(max_retries=3, retryable_exceptions=(httpx.RequestError,))
def get_weather(city: str) -> dict:
    """Get weather for a city."""
    response = httpx.get(f"{BASE_URL}/weather", params={"city": city})
    response.raise_for_status()
    return response.json()
```

### Retryable Errors

| Error Type | Retry? | Reason |
|------------|--------|--------|
| `httpx.ConnectTimeout` | Yes | Network transient |
| `httpx.ReadTimeout` | Yes | Server slow |
| `httpx.HTTPStatusError` (5xx) | Yes | Server error |
| `httpx.HTTPStatusError` (4xx) | No | Client error |
| `ValueError` | No | Input error |

---

## Circuit Breaker

Prevent cascading failures with circuit breaker pattern.

### Generated Code

```python
import time
from enum import Enum
from threading import Lock

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_requests: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_successes = 0
        self._lock = Lock()

    def can_execute(self) -> bool:
        """Check if request can proceed."""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_successes = 0
                    return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                return True

        return False

    def record_success(self):
        """Record successful request."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_successes += 1
                if self.half_open_successes >= self.half_open_requests:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0

    def record_failure(self):
        """Record failed request."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN

# Usage
weather_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)

@mcp.tool()
def get_weather(city: str) -> dict:
    """Get weather for a city."""
    if not weather_circuit.can_execute():
        return {"error": "Service temporarily unavailable"}

    try:
        response = httpx.get(f"{BASE_URL}/weather", params={"city": city})
        response.raise_for_status()
        weather_circuit.record_success()
        return response.json()
    except Exception as e:
        weather_circuit.record_failure()
        raise
```

---

## OpenTelemetry Integration

Distributed tracing for complex systems.

### Configuration

```python
config = ProductionConfig(
    enable_telemetry=True,
    telemetry_endpoint="http://jaeger:4317",
)
```

### Generated Code

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# Configure tracing
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://jaeger:4317"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

# Auto-instrument HTTP client
HTTPXClientInstrumentor().instrument()

@mcp.tool()
def get_weather(city: str) -> dict:
    """Get weather for a city."""
    with tracer.start_as_current_span("get_weather") as span:
        span.set_attribute("city", city)

        response = httpx.get(f"{BASE_URL}/weather", params={"city": city})

        span.set_attribute("http.status_code", response.status_code)
        return response.json()
```

---

## Health Check

All generated servers include a health check endpoint.

### Generated Code

```python
from datetime import datetime

@mcp.tool()
def health_check() -> dict:
    """Check server health and configuration status.

    Returns:
        Health status including auth configuration and uptime
    """
    auth_status = {}
    for key in AUTH_CONFIG:
        auth_status[key] = "configured" if AUTH_CONFIG[key] else "missing"

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "server_name": "MyServer",
        "auth_config": auth_status,
        "rate_limit": {
            "remaining": rate_limiter.get_remaining() if rate_limiter else None,
            "window_seconds": rate_limiter.window_seconds if rate_limiter else None,
        },
    }
```

### Response

```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00.000000",
  "server_name": "MyServer",
  "auth_config": {
    "API_KEY": "configured"
  },
  "rate_limit": {
    "remaining": 95,
    "window_seconds": 60
  }
}
```

---

## Docker Production Configuration

### Generated Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health')"

# Run server
CMD ["python", "server.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  mcp-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - API_KEY=${API_KEY}
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `RATE_LIMIT_REQUESTS` | Max requests per window | `100` |
| `RATE_LIMIT_WINDOW` | Rate limit window (seconds) | `60` |
| `METRICS_PORT` | Prometheus metrics port | `8000` |
| `OTEL_EXPORTER_ENDPOINT` | OpenTelemetry endpoint | - |
| `REDIS_URL` | Redis URL for distributed rate limiting | - |

---

## Best Practices

### 1. Enable All Production Features

```python
config = ProductionConfig(
    enable_logging=True,
    enable_metrics=True,
    enable_rate_limiting=True,
    enable_retries=True,
)
```

### 2. Use Appropriate Rate Limits

| Use Case | Requests/min | Window |
|----------|--------------|--------|
| Public API | 60 | 60s |
| Authenticated API | 1000 | 60s |
| Internal service | 10000 | 60s |

### 3. Configure Alerts

```yaml
# Prometheus alerting rules
groups:
  - name: mcp-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(mcp_tool_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical

      - alert: HighLatency
        expr: histogram_quantile(0.99, rate(mcp_tool_latency_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
```

### 4. Implement Graceful Shutdown

```python
import signal
import sys

def graceful_shutdown(signum, frame):
    StructuredLogger.info("Shutting down gracefully")
    # Finish in-flight requests
    # Close connections
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)
```
