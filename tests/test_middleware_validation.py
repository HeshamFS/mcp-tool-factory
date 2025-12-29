"""Tests for validation middleware module."""

import pytest
from tool_factory.middleware.validation import (
    ValidationError,
    ValidationType,
    SchemaValidator,
    RequestValidator,
    ResponseValidator,
    ValidationMiddleware,
    generate_validation_middleware_code,
)


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_basic_error(self):
        """Test basic validation error."""
        error = ValidationError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.errors == []
        assert error.field_path is None

    def test_error_with_details(self):
        """Test error with details."""
        error = ValidationError(
            "Multiple errors",
            errors=[{"field": "name", "error": "required"}],
            field_path="user.name",
        )
        assert error.errors == [{"field": "name", "error": "required"}]
        assert error.field_path == "user.name"

    def test_to_dict(self):
        """Test error serialization."""
        error = ValidationError(
            "Test",
            errors=[{"error": "bad"}],
            field_path="test.field",
        )
        d = error.to_dict()
        assert d["error"] == "Validation Error"
        assert d["message"] == "Test"
        assert d["details"] == [{"error": "bad"}]
        assert d["field"] == "test.field"


class TestSchemaValidator:
    """Tests for SchemaValidator."""

    def test_validate_string_valid(self):
        """Test valid string validation."""
        validator = SchemaValidator({"type": "string"})
        is_valid, value, errors = validator.validate("hello")
        assert is_valid
        assert value == "hello"
        assert errors == []

    def test_validate_string_coerce(self):
        """Test string type coercion."""
        validator = SchemaValidator({"type": "string"}, coerce_types=True)
        is_valid, value, errors = validator.validate(123)
        assert is_valid
        assert value == "123"

    def test_validate_string_min_length(self):
        """Test string minLength constraint."""
        validator = SchemaValidator({"type": "string", "minLength": 5})
        is_valid, _, errors = validator.validate("hi")
        assert not is_valid
        assert any("too short" in e for e in errors)

    def test_validate_string_max_length(self):
        """Test string maxLength constraint."""
        validator = SchemaValidator({"type": "string", "maxLength": 5})
        is_valid, _, errors = validator.validate("hello world")
        assert not is_valid
        assert any("too long" in e for e in errors)

    def test_validate_string_pattern(self):
        """Test string pattern constraint."""
        validator = SchemaValidator({"type": "string", "pattern": r"^\d+$"})
        is_valid, _, errors = validator.validate("abc")
        assert not is_valid
        assert any("pattern" in e for e in errors)

    def test_validate_string_enum(self):
        """Test string enum constraint."""
        validator = SchemaValidator({"type": "string", "enum": ["a", "b", "c"]})
        is_valid, _, errors = validator.validate("d")
        assert not is_valid
        assert any("one of" in e for e in errors)

    def test_validate_integer_valid(self):
        """Test valid integer validation."""
        validator = SchemaValidator({"type": "integer"})
        is_valid, value, errors = validator.validate(42)
        assert is_valid
        assert value == 42

    def test_validate_integer_coerce(self):
        """Test integer type coercion."""
        validator = SchemaValidator({"type": "integer"}, coerce_types=True)
        is_valid, value, errors = validator.validate("42")
        assert is_valid
        assert value == 42

    def test_validate_integer_rejects_bool(self):
        """Test integer rejects boolean."""
        validator = SchemaValidator({"type": "integer"})
        is_valid, _, errors = validator.validate(True)
        assert not is_valid
        assert any("boolean" in e for e in errors)

    def test_validate_integer_minimum(self):
        """Test integer minimum constraint."""
        validator = SchemaValidator({"type": "integer", "minimum": 10})
        is_valid, _, errors = validator.validate(5)
        assert not is_valid
        assert any("less than minimum" in e for e in errors)

    def test_validate_integer_maximum(self):
        """Test integer maximum constraint."""
        validator = SchemaValidator({"type": "integer", "maximum": 10})
        is_valid, _, errors = validator.validate(15)
        assert not is_valid
        assert any("greater than maximum" in e for e in errors)

    def test_validate_number_valid(self):
        """Test valid number validation."""
        validator = SchemaValidator({"type": "number"})
        is_valid, value, errors = validator.validate(3.14)
        assert is_valid
        assert value == 3.14

    def test_validate_number_nan(self):
        """Test number rejects NaN."""
        validator = SchemaValidator({"type": "number"})
        is_valid, _, errors = validator.validate(float("nan"))
        assert not is_valid
        assert any("finite" in e for e in errors)

    def test_validate_number_infinity(self):
        """Test number rejects infinity."""
        validator = SchemaValidator({"type": "number"})
        is_valid, _, errors = validator.validate(float("inf"))
        assert not is_valid
        assert any("finite" in e for e in errors)

    def test_validate_boolean_valid(self):
        """Test valid boolean validation."""
        validator = SchemaValidator({"type": "boolean"})
        is_valid, value, errors = validator.validate(True)
        assert is_valid
        assert value is True

    def test_validate_boolean_coerce(self):
        """Test boolean type coercion."""
        validator = SchemaValidator({"type": "boolean"}, coerce_types=True)

        is_valid, value, _ = validator.validate("true")
        assert is_valid
        assert value is True

        is_valid, value, _ = validator.validate(0)
        assert is_valid
        assert value is False

    def test_validate_object_valid(self):
        """Test valid object validation."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        }
        validator = SchemaValidator(schema)
        is_valid, value, errors = validator.validate({"name": "John", "age": 30})
        assert is_valid
        assert value == {"name": "John", "age": 30}

    def test_validate_object_required(self):
        """Test object required fields."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        validator = SchemaValidator(schema)
        is_valid, _, errors = validator.validate({})
        assert not is_valid
        assert any("required" in e.lower() for e in errors)

    def test_validate_object_additional_properties_false(self):
        """Test object additionalProperties: false."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False,
        }
        validator = SchemaValidator(schema)
        is_valid, _, errors = validator.validate({"name": "John", "extra": "value"})
        assert not is_valid
        assert any("Additional properties" in e for e in errors)

    def test_validate_array_valid(self):
        """Test valid array validation."""
        schema = {"type": "array", "items": {"type": "integer"}}
        validator = SchemaValidator(schema)
        is_valid, value, errors = validator.validate([1, 2, 3])
        assert is_valid
        assert value == [1, 2, 3]

    def test_validate_array_min_items(self):
        """Test array minItems constraint."""
        schema = {"type": "array", "items": {"type": "integer"}, "minItems": 3}
        validator = SchemaValidator(schema)
        is_valid, _, errors = validator.validate([1])
        assert not is_valid
        assert any("minimum" in e for e in errors)

    def test_validate_array_max_items(self):
        """Test array maxItems constraint."""
        schema = {"type": "array", "items": {"type": "integer"}, "maxItems": 2}
        validator = SchemaValidator(schema)
        is_valid, _, errors = validator.validate([1, 2, 3, 4])
        assert not is_valid
        assert any("maximum" in e for e in errors)

    def test_validate_anyof(self):
        """Test anyOf schema validation."""
        schema = {
            "anyOf": [
                {"type": "string"},
                {"type": "integer"},
            ]
        }
        validator = SchemaValidator(schema, coerce_types=False)

        is_valid, value, _ = validator.validate("hello")
        assert is_valid

        is_valid, value, _ = validator.validate(42)
        assert is_valid

        is_valid, _, errors = validator.validate([1, 2])
        assert not is_valid


class TestRequestValidator:
    """Tests for RequestValidator."""

    def test_add_and_validate_schema(self):
        """Test adding and validating schema."""
        validator = RequestValidator()
        validator.add_schema("get_user", {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        })

        is_valid, coerced, errors = validator.validate("get_user", {"id": 123})
        assert is_valid
        assert coerced == {"id": 123}

    def test_validate_unknown_tool(self):
        """Test validation of unknown tool."""
        validator = RequestValidator(strict_mode=False)
        is_valid, _, _ = validator.validate("unknown_tool", {"any": "data"})
        assert is_valid

    def test_validate_unknown_tool_strict(self):
        """Test strict mode rejects unknown tools."""
        validator = RequestValidator(strict_mode=True)
        is_valid, _, errors = validator.validate("unknown_tool", {})
        assert not is_valid
        assert any("No schema" in e for e in errors)

    def test_coerce_types(self):
        """Test type coercion in request validation."""
        validator = RequestValidator(coerce_types=True)
        validator.add_schema("test", {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
        })

        is_valid, coerced, _ = validator.validate("test", {"count": "42"})
        assert is_valid
        assert coerced["count"] == 42


class TestResponseValidator:
    """Tests for ResponseValidator."""

    def test_validate_response(self):
        """Test response validation."""
        validator = ResponseValidator()
        validator.add_schema("get_user", {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
        })

        is_valid, errors = validator.validate("get_user", {"id": 1, "name": "John"})
        assert is_valid

    def test_validate_invalid_response(self):
        """Test invalid response detection."""
        validator = ResponseValidator(log_warnings=False)
        validator.add_schema("get_user", {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
        })

        is_valid, errors = validator.validate("get_user", {"id": "not_an_int"})
        assert not is_valid


class TestValidationMiddleware:
    """Tests for ValidationMiddleware."""

    def test_register_tool(self):
        """Test tool registration."""
        middleware = ValidationMiddleware()
        middleware.register_tool(
            "test_tool",
            input_schema={"type": "object"},
            output_schema={"type": "string"},
        )

        assert "test_tool" in middleware.request_validator.schemas
        assert "test_tool" in middleware.response_validator.schemas

    def test_wrap_function_valid_input(self):
        """Test wrapper with valid input."""
        middleware = ValidationMiddleware()
        middleware.register_tool("add", {
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
        })

        @middleware.wrap("add")
        def add(a: int, b: int) -> int:
            return a + b

        result = add(a=1, b=2)
        assert result == 3

    def test_wrap_function_invalid_input(self):
        """Test wrapper raises on invalid input."""
        middleware = ValidationMiddleware(raise_on_request_error=True)
        middleware.register_tool("add", {
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
        })

        @middleware.wrap("add")
        def add(a: int, b: int) -> int:
            return a + b

        with pytest.raises(ValidationError):
            add(a=1)  # Missing b

    def test_wrap_function_coerces_input(self):
        """Test wrapper coerces input types."""
        middleware = ValidationMiddleware()
        middleware.request_validator.coerce_types = True
        middleware.register_tool("greet", {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
        })

        @middleware.wrap("greet")
        def greet(count: int) -> str:
            return f"Hello {count} times"

        result = greet(count="5")  # String should be coerced
        assert result == "Hello 5 times"

    def test_from_openapi(self):
        """Test creating middleware from OpenAPI spec."""
        spec = {
            "openapi": "3.0.0",
            "paths": {
                "/users": {
                    "post": {
                        "operationId": "createUser",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {"type": "object"}
                                    }
                                }
                            }
                        },
                    }
                }
            },
        }

        middleware = ValidationMiddleware.from_openapi(spec)
        assert "createUser" in middleware.request_validator.schemas


class TestGenerateValidationCode:
    """Tests for validation code generation."""

    def test_generate_basic_code(self):
        """Test basic validation code generation."""
        tool_specs = [
            {
                "name": "add_numbers",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"},
                    },
                    "required": ["a", "b"],
                },
            }
        ]

        code = generate_validation_middleware_code(tool_specs)

        assert "class ValidationError" in code
        assert "validate_schema" in code
        assert "TOOL_SCHEMAS" in code
        assert "add_numbers" in code
        assert "validate_tool_input" in code
        assert "with_validation" in code

    def test_generate_code_multiple_tools(self):
        """Test code generation with multiple tools."""
        tool_specs = [
            {"name": "tool1", "input_schema": {"type": "object"}},
            {"name": "tool2", "input_schema": {"type": "object"}},
            {"name": "tool3", "input_schema": {"type": "object"}},
        ]

        code = generate_validation_middleware_code(tool_specs)

        assert '"tool1"' in code
        assert '"tool2"' in code
        assert '"tool3"' in code

    def test_generated_code_is_valid_python(self):
        """Test generated code is syntactically valid."""
        tool_specs = [
            {
                "name": "test",
                "input_schema": {"type": "object", "properties": {"x": {"type": "integer"}}},
            }
        ]

        code = generate_validation_middleware_code(tool_specs)

        # Should not raise SyntaxError
        compile(code, "<generated>", "exec")
