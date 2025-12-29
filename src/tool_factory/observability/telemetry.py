"""OpenTelemetry integration for MCP servers.

Provides distributed tracing, metrics, and structured logging
for production MCP server deployments.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TelemetryExporter(Enum):
    """Supported telemetry exporters."""
    CONSOLE = "console"  # Debug output to console
    OTLP = "otlp"        # OpenTelemetry Protocol (default)
    JAEGER = "jaeger"    # Jaeger backend
    ZIPKIN = "zipkin"    # Zipkin backend
    AZURE = "azure"      # Azure Application Insights


@dataclass
class TelemetryConfig:
    """Configuration for OpenTelemetry integration."""

    # Basic settings
    enabled: bool = True
    service_name: str = "mcp-server"
    service_version: str = "1.0.0"

    # Tracing settings
    enable_tracing: bool = True
    exporter: TelemetryExporter = TelemetryExporter.OTLP
    endpoint: str = "http://localhost:4317"
    sample_rate: float = 1.0  # 1.0 = 100% sampling

    # Metrics settings
    enable_metrics: bool = True
    metrics_port: int = 9464  # Prometheus metrics port

    # Logging settings
    enable_log_correlation: bool = True

    # Azure-specific settings (only used when exporter is AZURE)
    azure_connection_string: str | None = None

    # Additional resource attributes
    resource_attributes: dict[str, str] = field(default_factory=dict)


class TelemetryCodeGenerator:
    """Generate OpenTelemetry instrumentation code for MCP servers."""

    def __init__(self, config: TelemetryConfig | None = None):
        self.config = config or TelemetryConfig()

    def generate_imports(self) -> str:
        """Generate import statements for telemetry."""
        if not self.config.enabled:
            return ""

        imports = [
            "import logging",
            "from contextlib import contextmanager",
            "from functools import wraps",
            "import time",
        ]

        if self.config.enable_tracing:
            imports.extend([
                "from opentelemetry import trace",
                "from opentelemetry.sdk.trace import TracerProvider",
                "from opentelemetry.sdk.trace.export import BatchSpanProcessor",
                "from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION",
                "from opentelemetry.trace import Status, StatusCode",
            ])

            # Exporter-specific imports
            if self.config.exporter == TelemetryExporter.OTLP:
                imports.append("from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter")
            elif self.config.exporter == TelemetryExporter.JAEGER:
                imports.append("from opentelemetry.exporter.jaeger.thrift import JaegerExporter")
            elif self.config.exporter == TelemetryExporter.ZIPKIN:
                imports.append("from opentelemetry.exporter.zipkin.json import ZipkinExporter")
            elif self.config.exporter == TelemetryExporter.AZURE:
                imports.append("from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter")
            elif self.config.exporter == TelemetryExporter.CONSOLE:
                imports.append("from opentelemetry.sdk.trace.export import ConsoleSpanExporter")

        if self.config.enable_metrics:
            imports.extend([
                "from opentelemetry import metrics",
                "from opentelemetry.sdk.metrics import MeterProvider",
                "from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader",
            ])

            if self.config.exporter == TelemetryExporter.OTLP:
                imports.append("from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter")
            elif self.config.exporter == TelemetryExporter.CONSOLE:
                imports.append("from opentelemetry.sdk.metrics.export import ConsoleMetricExporter")

        if self.config.enable_log_correlation:
            imports.extend([
                "from opentelemetry.instrumentation.logging import LoggingInstrumentor",
            ])

        return "\n".join(imports)

    def generate_setup_code(self) -> str:
        """Generate telemetry setup code."""
        if not self.config.enabled:
            return ""

        # Build resource attributes
        resource_attrs = {
            "SERVICE_NAME": self.config.service_name,
            "SERVICE_VERSION": self.config.service_version,
        }
        resource_attrs.update(self.config.resource_attributes)

        code = f'''
# ============== OPENTELEMETRY SETUP ==============

def setup_telemetry():
    """Initialize OpenTelemetry instrumentation."""

    # Create resource with service information
    resource = Resource(attributes={{
        SERVICE_NAME: "{self.config.service_name}",
        SERVICE_VERSION: "{self.config.service_version}",
'''

        # Add custom resource attributes
        for key, value in self.config.resource_attributes.items():
            code += f'        "{key}": "{value}",\n'

        code += "    })\n"

        # Tracing setup
        if self.config.enable_tracing:
            code += self._generate_tracing_setup()

        # Metrics setup
        if self.config.enable_metrics:
            code += self._generate_metrics_setup()

        # Log correlation
        if self.config.enable_log_correlation:
            code += '''
    # Enable log correlation with trace context
    LoggingInstrumentor().instrument()
'''

        code += '''
    logger = logging.getLogger("mcp_server.telemetry")
    logger.info("OpenTelemetry instrumentation initialized")


# Initialize telemetry on module load
setup_telemetry()

'''
        return code

    def _generate_tracing_setup(self) -> str:
        """Generate tracing setup code."""
        code = "\n    # Setup tracing\n"
        code += "    tracer_provider = TracerProvider(resource=resource)\n"

        # Exporter configuration
        if self.config.exporter == TelemetryExporter.OTLP:
            code += f'''    exporter = OTLPSpanExporter(endpoint="{self.config.endpoint}")
'''
        elif self.config.exporter == TelemetryExporter.JAEGER:
            # Parse endpoint for Jaeger
            code += f'''    exporter = JaegerExporter(
        agent_host_name="{self.config.endpoint.split('://')[1].split(':')[0]}",
        agent_port=6831,
    )
'''
        elif self.config.exporter == TelemetryExporter.ZIPKIN:
            code += f'''    exporter = ZipkinExporter(endpoint="{self.config.endpoint}/api/v2/spans")
'''
        elif self.config.exporter == TelemetryExporter.AZURE:
            code += f'''    exporter = AzureMonitorTraceExporter(
        connection_string="{self.config.azure_connection_string or ''}"
    )
'''
        elif self.config.exporter == TelemetryExporter.CONSOLE:
            code += "    exporter = ConsoleSpanExporter()\n"

        code += """    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)
"""
        return code

    def _generate_metrics_setup(self) -> str:
        """Generate metrics setup code."""
        code = "\n    # Setup metrics\n"

        if self.config.exporter == TelemetryExporter.OTLP:
            code += f'''    metric_exporter = OTLPMetricExporter(endpoint="{self.config.endpoint}")
'''
        elif self.config.exporter == TelemetryExporter.CONSOLE:
            code += "    metric_exporter = ConsoleMetricExporter()\n"
        else:
            # Use OTLP as fallback for other exporters
            code += f'''    metric_exporter = OTLPMetricExporter(endpoint="{self.config.endpoint}")
'''

        code += """    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
"""
        return code

    def generate_instrumentation_code(self) -> str:
        """Generate tool instrumentation utilities."""
        if not self.config.enabled:
            return ""

        code = '''
# ============== TELEMETRY UTILITIES ==============

# Get tracer for MCP server
tracer = trace.get_tracer("mcp_server")

# Get meter for metrics
meter = metrics.get_meter("mcp_server")

# Create metrics
tool_call_counter = meter.create_counter(
    "mcp.tool.calls",
    description="Number of tool calls",
    unit="1",
)

tool_duration_histogram = meter.create_histogram(
    "mcp.tool.duration",
    description="Tool call duration",
    unit="ms",
)

tool_error_counter = meter.create_counter(
    "mcp.tool.errors",
    description="Number of tool errors",
    unit="1",
)


@contextmanager
def trace_tool_call(tool_name: str, arguments: dict | None = None):
    """Context manager for tracing a tool call.

    Usage:
        with trace_tool_call("my_tool", {"arg": "value"}) as span:
            result = do_work()
            span.set_attribute("result.size", len(result))
    """
    with tracer.start_as_current_span(
        f"tool.{tool_name}",
        kind=trace.SpanKind.INTERNAL,
    ) as span:
        start_time = time.time()

        # Set input attributes
        span.set_attribute("tool.name", tool_name)
        if arguments:
            for key, value in arguments.items():
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(f"tool.input.{key}", value)

        try:
            yield span

            # Record success
            span.set_status(Status(StatusCode.OK))
            tool_call_counter.add(1, {"tool": tool_name, "status": "success"})

        except Exception as e:
            # Record error
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            tool_error_counter.add(1, {"tool": tool_name, "error_type": type(e).__name__})
            tool_call_counter.add(1, {"tool": tool_name, "status": "error"})
            raise

        finally:
            # Record duration
            duration_ms = (time.time() - start_time) * 1000
            span.set_attribute("tool.duration_ms", duration_ms)
            tool_duration_histogram.record(duration_ms, {"tool": tool_name})


def instrument_tool(tool_name: str):
    """Decorator to add tracing to a tool function.

    Usage:
        @instrument_tool("my_tool")
        def my_tool(arg1: str) -> str:
            return f"Hello {arg1}"
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with trace_tool_call(tool_name, kwargs) as span:
                result = func(*args, **kwargs)

                # Add result info to span
                if isinstance(result, str):
                    span.set_attribute("tool.result.length", len(result))
                elif isinstance(result, dict):
                    span.set_attribute("tool.result.keys", str(list(result.keys())))

                return result
        return wrapper
    return decorator


async def async_instrument_tool(tool_name: str):
    """Decorator to add tracing to an async tool function."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with trace_tool_call(tool_name, kwargs) as span:
                result = await func(*args, **kwargs)

                if isinstance(result, str):
                    span.set_attribute("tool.result.length", len(result))
                elif isinstance(result, dict):
                    span.set_attribute("tool.result.keys", str(list(result.keys())))

                return result
        return wrapper
    return decorator

'''
        return code

    def generate_all(self) -> str:
        """Generate all telemetry code."""
        if not self.config.enabled:
            return "# Telemetry disabled\n"

        parts = [
            self.generate_imports(),
            "",
            self.generate_setup_code(),
            self.generate_instrumentation_code(),
        ]
        return "\n".join(parts)


def generate_telemetry_code(config: TelemetryConfig | None = None) -> str:
    """Generate OpenTelemetry instrumentation code.

    Args:
        config: Telemetry configuration

    Returns:
        Python code string for telemetry integration
    """
    generator = TelemetryCodeGenerator(config)
    return generator.generate_all()
