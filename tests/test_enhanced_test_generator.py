"""Tests for enhanced test generator."""

import pytest
from tool_factory.generators.tests import (
    TestCase,
    TestGeneratorConfig,
    EnhancedTestGenerator,
    generate_enhanced_tests,
)


class TestTestCase:
    """Tests for TestCase dataclass."""

    def test_basic_test_case(self):
        """Test basic test case creation."""
        tc = TestCase(
            name="test_add",
            description="Test addition",
            tool_name="add",
            inputs={"a": 1, "b": 2},
        )
        assert tc.name == "test_add"
        assert tc.expected_success is True

    def test_error_test_case(self):
        """Test error test case."""
        tc = TestCase(
            name="test_fail",
            description="Test failure",
            tool_name="fail",
            inputs={},
            expected_success=False,
            expected_error="Missing required field",
        )
        assert tc.expected_success is False
        assert tc.expected_error == "Missing required field"


class TestTestGeneratorConfig:
    """Tests for TestGeneratorConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = TestGeneratorConfig()
        assert config.generate_existence_tests is True
        assert config.generate_functional_tests is True
        assert config.generate_error_tests is True
        assert config.generate_boundary_tests is True
        assert config.generate_validation_tests is True
        assert config.use_mocking is True
        assert config.async_tests is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = TestGeneratorConfig(
            generate_existence_tests=False,
            generate_functional_tests=True,
            generate_error_tests=False,
        )
        assert config.generate_existence_tests is False
        assert config.generate_functional_tests is True
        assert config.generate_error_tests is False


class TestEnhancedTestGenerator:
    """Tests for EnhancedTestGenerator."""

    @pytest.fixture
    def sample_tool_specs(self):
        """Sample tool specifications."""
        return [
            {
                "name": "add_numbers",
                "description": "Add two numbers together",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"},
                    },
                    "required": ["a", "b"],
                },
            },
            {
                "name": "greet_user",
                "description": "Greet a user by name",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "maxLength": 100},
                        "formal": {"type": "boolean"},
                    },
                    "required": ["name"],
                },
            },
        ]

    def test_generate_tests_creates_file(self, sample_tool_specs):
        """Test generate_tests creates test content."""
        generator = EnhancedTestGenerator()
        code = generator.generate_tests("test_server", sample_tool_specs)

        assert "import pytest" in code
        assert "test_server" in code

    def test_generates_existence_tests(self, sample_tool_specs):
        """Test existence tests are generated."""
        generator = EnhancedTestGenerator()
        code = generator.generate_tests("test_server", sample_tool_specs)

        assert "TestToolExistence" in code
        assert "test_all_tools_registered" in code
        assert "add_numbers" in code
        assert "greet_user" in code

    def test_generates_functional_tests(self, sample_tool_specs):
        """Test functional tests are generated."""
        generator = EnhancedTestGenerator()
        code = generator.generate_tests("test_server", sample_tool_specs)

        assert "TestToolFunctionality" in code
        assert "test_add_numbers_with_valid_input" in code
        assert "test_greet_user_with_valid_input" in code

    def test_generates_error_tests(self, sample_tool_specs):
        """Test error tests are generated."""
        generator = EnhancedTestGenerator()
        code = generator.generate_tests("test_server", sample_tool_specs)

        assert "TestToolErrors" in code
        assert "test_unknown_tool_raises" in code
        assert "missing_required_field" in code

    def test_generates_boundary_tests(self, sample_tool_specs):
        """Test boundary tests are generated."""
        generator = EnhancedTestGenerator()
        code = generator.generate_tests("test_server", sample_tool_specs)

        assert "TestToolBoundaries" in code
        assert "zero_values" in code or "empty_strings" in code

    def test_generates_validation_tests(self, sample_tool_specs):
        """Test validation tests are generated."""
        generator = EnhancedTestGenerator()
        code = generator.generate_tests("test_server", sample_tool_specs)

        assert "TestInputValidation" in code
        assert "rejects_string" in code

    def test_can_disable_test_types(self, sample_tool_specs):
        """Test disabling specific test types."""
        config = TestGeneratorConfig(
            generate_existence_tests=False,
            generate_error_tests=False,
        )
        generator = EnhancedTestGenerator(config)
        code = generator.generate_tests("test_server", sample_tool_specs)

        assert "TestToolExistence" not in code
        assert "TestToolErrors" not in code
        assert "TestToolFunctionality" in code

    def test_generates_sample_inputs_string(self, sample_tool_specs):
        """Test sample input generation for strings."""
        generator = EnhancedTestGenerator()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }
        inputs = generator._generate_sample_inputs(schema)
        assert "name" in inputs
        assert isinstance(inputs["name"], str)

    def test_generates_sample_inputs_number(self, sample_tool_specs):
        """Test sample input generation for numbers."""
        generator = EnhancedTestGenerator()
        schema = {
            "type": "object",
            "properties": {
                "value": {"type": "number", "minimum": 0, "maximum": 100},
            },
        }
        inputs = generator._generate_sample_inputs(schema)
        assert "value" in inputs
        assert inputs["value"] == 50.0

    def test_generates_sample_inputs_integer(self, sample_tool_specs):
        """Test sample input generation for integers."""
        generator = EnhancedTestGenerator()
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "minimum": 1, "maximum": 10},
            },
        }
        inputs = generator._generate_sample_inputs(schema)
        assert "count" in inputs
        assert inputs["count"] == 5

    def test_generates_sample_inputs_boolean(self, sample_tool_specs):
        """Test sample input generation for booleans."""
        generator = EnhancedTestGenerator()
        schema = {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
            },
        }
        inputs = generator._generate_sample_inputs(schema)
        assert inputs["enabled"] is True

    def test_generates_sample_inputs_enum(self, sample_tool_specs):
        """Test sample input generation for enums."""
        generator = EnhancedTestGenerator()
        schema = {
            "type": "object",
            "properties": {
                "color": {"type": "string", "enum": ["red", "green", "blue"]},
            },
        }
        inputs = generator._generate_sample_inputs(schema)
        assert inputs["color"] == "red"

    def test_generates_sample_inputs_email(self, sample_tool_specs):
        """Test sample input generation for email format."""
        generator = EnhancedTestGenerator()
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
            },
        }
        inputs = generator._generate_sample_inputs(schema)
        assert inputs["email"] == "test@example.com"

    def test_generates_sample_inputs_uri(self, sample_tool_specs):
        """Test sample input generation for URI format."""
        generator = EnhancedTestGenerator()
        schema = {
            "type": "object",
            "properties": {
                "url": {"type": "string", "format": "uri"},
            },
        }
        inputs = generator._generate_sample_inputs(schema)
        assert inputs["url"] == "https://example.com"

    def test_generates_sample_inputs_array(self, sample_tool_specs):
        """Test sample input generation for arrays."""
        generator = EnhancedTestGenerator()
        schema = {
            "type": "object",
            "properties": {
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        }
        inputs = generator._generate_sample_inputs(schema)
        assert inputs["tags"] == ["item1", "item2"]

    def test_generated_code_is_valid_python(self, sample_tool_specs):
        """Test generated code is syntactically valid."""
        generator = EnhancedTestGenerator()
        code = generator.generate_tests("test_server", sample_tool_specs)

        # Should not raise SyntaxError
        compile(code, "<generated>", "exec")


class TestGenerateEnhancedTests:
    """Tests for generate_enhanced_tests convenience function."""

    def test_with_default_config(self):
        """Test with default configuration."""
        tool_specs = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "input_schema": {"type": "object", "properties": {}},
            }
        ]
        code = generate_enhanced_tests("my_server", tool_specs)

        assert "my_server" in code
        assert "test_tool" in code

    def test_with_custom_config(self):
        """Test with custom configuration."""
        config = TestGeneratorConfig(
            generate_boundary_tests=False,
            generate_validation_tests=False,
        )
        tool_specs = [
            {
                "name": "simple_tool",
                "description": "Simple",
                "input_schema": {"type": "object"},
            }
        ]
        code = generate_enhanced_tests("server", tool_specs, config)

        assert "TestToolBoundaries" not in code
        assert "TestInputValidation" not in code

    def test_empty_tool_specs(self):
        """Test with empty tool specs."""
        code = generate_enhanced_tests("empty_server", [])

        assert "empty_server" in code
        assert "import pytest" in code
        # Should still be valid Python
        compile(code, "<generated>", "exec")
