"""Tests for observability/telemetry module."""

from tool_factory.observability import (
    TelemetryCodeGenerator,
    TelemetryConfig,
    TelemetryExporter,
    generate_telemetry_code,
)


class TestTelemetryExporter:
    """Tests for TelemetryExporter enum."""

    def test_exporter_values(self):
        """Test all exporter values are defined."""
        assert TelemetryExporter.CONSOLE.value == "console"
        assert TelemetryExporter.OTLP.value == "otlp"
        assert TelemetryExporter.JAEGER.value == "jaeger"
        assert TelemetryExporter.ZIPKIN.value == "zipkin"
        assert TelemetryExporter.AZURE.value == "azure"


class TestTelemetryConfig:
    """Tests for TelemetryConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TelemetryConfig()

        assert config.enabled is True
        assert config.service_name == "mcp-server"
        assert config.service_version == "1.0.0"
        assert config.enable_tracing is True
        assert config.exporter == TelemetryExporter.OTLP
        assert config.endpoint == "http://localhost:4317"
        assert config.sample_rate == 1.0
        assert config.enable_metrics is True
        assert config.metrics_port == 9464
        assert config.enable_log_correlation is True
        assert config.azure_connection_string is None
        assert config.resource_attributes == {}

    def test_custom_values(self):
        """Test custom configuration values."""
        config = TelemetryConfig(
            service_name="my-mcp-server",
            service_version="2.0.0",
            exporter=TelemetryExporter.JAEGER,
            endpoint="http://jaeger:14268",
            sample_rate=0.5,
            resource_attributes={"environment": "production"},
        )

        assert config.service_name == "my-mcp-server"
        assert config.service_version == "2.0.0"
        assert config.exporter == TelemetryExporter.JAEGER
        assert config.endpoint == "http://jaeger:14268"
        assert config.sample_rate == 0.5
        assert config.resource_attributes == {"environment": "production"}


class TestTelemetryCodeGenerator:
    """Tests for TelemetryCodeGenerator."""

    def test_disabled_generates_empty(self):
        """Test disabled config generates minimal code."""
        config = TelemetryConfig(enabled=False)
        gen = TelemetryCodeGenerator(config)

        imports = gen.generate_imports()
        setup = gen.generate_setup_code()
        instrumentation = gen.generate_instrumentation_code()

        assert imports == ""
        assert setup == ""
        assert instrumentation == ""

    def test_generate_imports_otlp(self):
        """Test import generation for OTLP exporter."""
        config = TelemetryConfig(
            exporter=TelemetryExporter.OTLP,
            enable_tracing=True,
            enable_metrics=True,
        )
        gen = TelemetryCodeGenerator(config)
        imports = gen.generate_imports()

        assert "from opentelemetry import trace" in imports
        assert "OTLPSpanExporter" in imports
        assert "from opentelemetry import metrics" in imports
        assert "OTLPMetricExporter" in imports

    def test_generate_imports_jaeger(self):
        """Test import generation for Jaeger exporter."""
        config = TelemetryConfig(exporter=TelemetryExporter.JAEGER)
        gen = TelemetryCodeGenerator(config)
        imports = gen.generate_imports()

        assert "JaegerExporter" in imports

    def test_generate_imports_zipkin(self):
        """Test import generation for Zipkin exporter."""
        config = TelemetryConfig(exporter=TelemetryExporter.ZIPKIN)
        gen = TelemetryCodeGenerator(config)
        imports = gen.generate_imports()

        assert "ZipkinExporter" in imports

    def test_generate_imports_azure(self):
        """Test import generation for Azure exporter."""
        config = TelemetryConfig(exporter=TelemetryExporter.AZURE)
        gen = TelemetryCodeGenerator(config)
        imports = gen.generate_imports()

        assert "AzureMonitorTraceExporter" in imports

    def test_generate_imports_console(self):
        """Test import generation for Console exporter."""
        config = TelemetryConfig(exporter=TelemetryExporter.CONSOLE)
        gen = TelemetryCodeGenerator(config)
        imports = gen.generate_imports()

        assert "ConsoleSpanExporter" in imports
        assert "ConsoleMetricExporter" in imports

    def test_generate_imports_log_correlation(self):
        """Test import generation with log correlation."""
        config = TelemetryConfig(enable_log_correlation=True)
        gen = TelemetryCodeGenerator(config)
        imports = gen.generate_imports()

        assert "LoggingInstrumentor" in imports

    def test_generate_setup_code_includes_service_info(self):
        """Test setup code includes service information."""
        config = TelemetryConfig(
            service_name="test-service",
            service_version="3.0.0",
        )
        gen = TelemetryCodeGenerator(config)
        code = gen.generate_setup_code()

        assert "test-service" in code
        assert "3.0.0" in code

    def test_generate_setup_code_includes_resource_attributes(self):
        """Test setup code includes resource attributes."""
        config = TelemetryConfig(
            resource_attributes={
                "environment": "production",
                "region": "us-east-1",
            }
        )
        gen = TelemetryCodeGenerator(config)
        code = gen.generate_setup_code()

        assert '"environment": "production"' in code
        assert '"region": "us-east-1"' in code

    def test_generate_setup_otlp(self):
        """Test setup code for OTLP exporter."""
        config = TelemetryConfig(
            exporter=TelemetryExporter.OTLP,
            endpoint="http://collector:4317",
        )
        gen = TelemetryCodeGenerator(config)
        code = gen.generate_setup_code()

        assert "OTLPSpanExporter" in code
        assert "http://collector:4317" in code

    def test_generate_setup_jaeger(self):
        """Test setup code for Jaeger exporter."""
        config = TelemetryConfig(
            exporter=TelemetryExporter.JAEGER,
            endpoint="http://jaeger-host:14268",
        )
        gen = TelemetryCodeGenerator(config)
        code = gen.generate_setup_code()

        assert "JaegerExporter" in code
        assert "jaeger-host" in code

    def test_generate_setup_zipkin(self):
        """Test setup code for Zipkin exporter."""
        config = TelemetryConfig(
            exporter=TelemetryExporter.ZIPKIN,
            endpoint="http://zipkin:9411",
        )
        gen = TelemetryCodeGenerator(config)
        code = gen.generate_setup_code()

        assert "ZipkinExporter" in code
        assert "http://zipkin:9411/api/v2/spans" in code

    def test_generate_setup_azure(self):
        """Test setup code for Azure exporter."""
        config = TelemetryConfig(
            exporter=TelemetryExporter.AZURE,
            azure_connection_string="InstrumentationKey=xxx",
        )
        gen = TelemetryCodeGenerator(config)
        code = gen.generate_setup_code()

        assert "AzureMonitorTraceExporter" in code
        assert "InstrumentationKey=xxx" in code

    def test_generate_instrumentation_code(self):
        """Test instrumentation code generation."""
        config = TelemetryConfig()
        gen = TelemetryCodeGenerator(config)
        code = gen.generate_instrumentation_code()

        assert "tracer = trace.get_tracer" in code
        assert "meter = metrics.get_meter" in code
        assert "tool_call_counter" in code
        assert "tool_duration_histogram" in code
        assert "tool_error_counter" in code
        assert "trace_tool_call" in code
        assert "instrument_tool" in code
        assert "async_instrument_tool" in code

    def test_generate_all(self):
        """Test generate_all includes all parts."""
        config = TelemetryConfig()
        gen = TelemetryCodeGenerator(config)
        code = gen.generate_all()

        # Imports
        assert "from opentelemetry import trace" in code

        # Setup
        assert "def setup_telemetry()" in code
        assert "setup_telemetry()" in code

        # Instrumentation
        assert "def instrument_tool" in code

    def test_generate_all_disabled(self):
        """Test generate_all when disabled."""
        config = TelemetryConfig(enabled=False)
        gen = TelemetryCodeGenerator(config)
        code = gen.generate_all()

        assert "Telemetry disabled" in code
        assert "opentelemetry" not in code


class TestGenerateTelemetryCode:
    """Tests for generate_telemetry_code convenience function."""

    def test_with_default_config(self):
        """Test with default configuration."""
        code = generate_telemetry_code()

        assert "opentelemetry" in code
        assert "setup_telemetry" in code
        assert "instrument_tool" in code

    def test_with_custom_config(self):
        """Test with custom configuration."""
        config = TelemetryConfig(
            service_name="custom-service",
            exporter=TelemetryExporter.JAEGER,
        )
        code = generate_telemetry_code(config)

        assert "custom-service" in code
        assert "JaegerExporter" in code

    def test_generates_valid_python(self):
        """Test generated code is syntactically valid."""
        code = generate_telemetry_code()

        # Should not raise SyntaxError
        compile(code, "<generated>", "exec")

    def test_generates_valid_python_all_exporters(self):
        """Test all exporter configurations generate valid code."""
        for exporter in TelemetryExporter:
            config = TelemetryConfig(exporter=exporter)
            code = generate_telemetry_code(config)

            # Should not raise SyntaxError
            compile(code, "<generated>", "exec")
