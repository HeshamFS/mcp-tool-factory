"""Tests for input validation utilities."""

import math
import pytest
from tool_factory.utils.input_validation import (
    ValidationResult,
    InputValidator,
    validate_finite,
    validate_string,
    validate_integer,
    validate_number,
    validate_url,
    validate_email,
    validate_path,
    sanitize_string,
    generate_validation_utilities_code,
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_success(self):
        """Test success factory method."""
        result = ValidationResult.success("value")
        assert result.is_valid is True
        assert result.value == "value"
        assert result.error is None

    def test_failure(self):
        """Test failure factory method."""
        result = ValidationResult.failure("error message", "bad_value")
        assert result.is_valid is False
        assert result.value == "bad_value"
        assert result.error == "error message"


class TestValidateFinite:
    """Tests for validate_finite function."""

    def test_valid_integer(self):
        """Test valid integer."""
        result = validate_finite(42)
        assert result.is_valid
        assert result.value == 42

    def test_valid_float(self):
        """Test valid float."""
        result = validate_finite(3.14)
        assert result.is_valid
        assert result.value == 3.14

    def test_rejects_nan(self):
        """Test NaN rejection."""
        result = validate_finite(float("nan"), "test_field")
        assert not result.is_valid
        assert "NaN" in result.error

    def test_rejects_infinity(self):
        """Test infinity rejection."""
        result = validate_finite(float("inf"), "test_field")
        assert not result.is_valid
        assert "infinity" in result.error

    def test_rejects_negative_infinity(self):
        """Test negative infinity rejection."""
        result = validate_finite(float("-inf"))
        assert not result.is_valid

    def test_rejects_non_number(self):
        """Test non-number rejection."""
        result = validate_finite("not a number")
        assert not result.is_valid
        assert "must be a number" in result.error


class TestValidateString:
    """Tests for validate_string function."""

    def test_valid_string(self):
        """Test valid string."""
        result = validate_string("hello")
        assert result.is_valid
        assert result.value == "hello"

    def test_strips_whitespace(self):
        """Test whitespace stripping."""
        result = validate_string("  hello  ")
        assert result.is_valid
        assert result.value == "hello"

    def test_coerces_to_string(self):
        """Test type coercion."""
        result = validate_string(123)
        assert result.is_valid
        assert result.value == "123"

    def test_rejects_null(self):
        """Test null rejection."""
        result = validate_string(None, "test")
        assert not result.is_valid
        assert "null" in result.error

    def test_min_length(self):
        """Test minimum length constraint."""
        result = validate_string("ab", "name", min_length=3)
        assert not result.is_valid
        assert "at least 3" in result.error

    def test_max_length(self):
        """Test maximum length constraint."""
        result = validate_string("abcdef", "name", max_length=5)
        assert not result.is_valid
        assert "at most 5" in result.error

    def test_pattern(self):
        """Test pattern constraint."""
        result = validate_string("abc123", "code", pattern=r"^[A-Z]+$")
        assert not result.is_valid
        assert "pattern" in result.error

    def test_pattern_valid(self):
        """Test valid pattern match."""
        result = validate_string("ABC", "code", pattern=r"^[A-Z]+$")
        assert result.is_valid

    def test_allowed_values(self):
        """Test enum constraint."""
        result = validate_string("d", "choice", allowed_values=["a", "b", "c"])
        assert not result.is_valid
        assert "one of" in result.error

    def test_allowed_values_valid(self):
        """Test valid enum value."""
        result = validate_string("b", "choice", allowed_values=["a", "b", "c"])
        assert result.is_valid


class TestValidateInteger:
    """Tests for validate_integer function."""

    def test_valid_integer(self):
        """Test valid integer."""
        result = validate_integer(42)
        assert result.is_valid
        assert result.value == 42

    def test_coerces_string(self):
        """Test string coercion."""
        result = validate_integer("42")
        assert result.is_valid
        assert result.value == 42

    def test_rejects_bool(self):
        """Test boolean rejection."""
        result = validate_integer(True)
        assert not result.is_valid
        assert "boolean" in result.error

    def test_minimum(self):
        """Test minimum constraint."""
        result = validate_integer(5, "age", minimum=18)
        assert not result.is_valid
        assert "at least 18" in result.error

    def test_maximum(self):
        """Test maximum constraint."""
        result = validate_integer(200, "age", maximum=150)
        assert not result.is_valid
        assert "at most 150" in result.error

    def test_no_coerce(self):
        """Test without coercion."""
        result = validate_integer("42", coerce=False)
        assert not result.is_valid


class TestValidateNumber:
    """Tests for validate_number function."""

    def test_valid_float(self):
        """Test valid float."""
        result = validate_number(3.14)
        assert result.is_valid
        assert result.value == 3.14

    def test_valid_integer(self):
        """Test integer as number."""
        result = validate_number(42)
        assert result.is_valid

    def test_coerces_string(self):
        """Test string coercion."""
        result = validate_number("3.14")
        assert result.is_valid
        assert result.value == 3.14

    def test_rejects_bool(self):
        """Test boolean rejection."""
        result = validate_number(False)
        assert not result.is_valid

    def test_rejects_nan_by_default(self):
        """Test NaN rejection by default."""
        result = validate_number(float("nan"))
        assert not result.is_valid

    def test_allows_nan_when_specified(self):
        """Test NaN allowed when specified."""
        result = validate_number(float("nan"), allow_nan=True)
        assert result.is_valid

    def test_rejects_infinity_by_default(self):
        """Test infinity rejection by default."""
        result = validate_number(float("inf"))
        assert not result.is_valid

    def test_allows_infinity_when_specified(self):
        """Test infinity allowed when specified."""
        result = validate_number(float("inf"), allow_infinity=True)
        assert result.is_valid

    def test_minimum(self):
        """Test minimum constraint."""
        result = validate_number(0.5, "ratio", minimum=1.0)
        assert not result.is_valid

    def test_maximum(self):
        """Test maximum constraint."""
        result = validate_number(1.5, "ratio", maximum=1.0)
        assert not result.is_valid


class TestValidateUrl:
    """Tests for validate_url function."""

    def test_valid_https(self):
        """Test valid HTTPS URL."""
        result = validate_url("https://example.com/path")
        assert result.is_valid

    def test_valid_http(self):
        """Test valid HTTP URL."""
        result = validate_url("http://example.com")
        assert result.is_valid

    def test_rejects_no_scheme(self):
        """Test rejection of URL without scheme."""
        result = validate_url("example.com")
        assert not result.is_valid
        assert "scheme" in result.error

    def test_rejects_invalid_scheme(self):
        """Test rejection of invalid scheme."""
        result = validate_url("ftp://example.com")
        assert not result.is_valid

    def test_allows_custom_schemes(self):
        """Test custom allowed schemes."""
        result = validate_url("ftp://example.com", allowed_schemes=["ftp"])
        assert result.is_valid

    def test_rejects_no_host(self):
        """Test rejection of URL without host."""
        result = validate_url("https:///path")
        assert not result.is_valid

    def test_allows_localhost(self):
        """Test localhost is allowed."""
        result = validate_url("http://localhost:8080")
        assert result.is_valid


class TestValidateEmail:
    """Tests for validate_email function."""

    def test_valid_email(self):
        """Test valid email."""
        result = validate_email("user@example.com")
        assert result.is_valid

    def test_valid_email_with_plus(self):
        """Test email with plus addressing."""
        result = validate_email("user+tag@example.com")
        assert result.is_valid

    def test_rejects_no_at(self):
        """Test rejection of email without @."""
        result = validate_email("userexample.com")
        assert not result.is_valid

    def test_rejects_no_domain(self):
        """Test rejection of email without domain."""
        result = validate_email("user@")
        assert not result.is_valid

    def test_rejects_no_tld(self):
        """Test rejection of email without TLD."""
        result = validate_email("user@example")
        assert not result.is_valid


class TestValidatePath:
    """Tests for validate_path function."""

    def test_valid_relative_path(self):
        """Test valid relative path."""
        result = validate_path("folder/file.txt")
        assert result.is_valid

    def test_valid_absolute_unix(self):
        """Test valid Unix absolute path."""
        result = validate_path("/home/user/file.txt", must_be_absolute=True)
        assert result.is_valid

    def test_valid_absolute_windows(self):
        """Test valid Windows absolute path."""
        result = validate_path("C:\\Users\\file.txt", must_be_absolute=True)
        assert result.is_valid

    def test_rejects_traversal(self):
        """Test rejection of path traversal."""
        result = validate_path("../etc/passwd")
        assert not result.is_valid
        assert "traversal" in result.error

    def test_allows_traversal_when_specified(self):
        """Test path traversal allowed when specified."""
        result = validate_path("../file.txt", disallow_traversal=False)
        assert result.is_valid

    def test_relative_when_absolute_required(self):
        """Test rejection of relative path when absolute required."""
        result = validate_path("folder/file.txt", must_be_absolute=True)
        assert not result.is_valid

    def test_allowed_extensions(self):
        """Test allowed extensions constraint."""
        result = validate_path("file.exe", allowed_extensions=[".txt", ".md"])
        assert not result.is_valid
        assert "extension" in result.error

    def test_allowed_extensions_valid(self):
        """Test valid extension."""
        result = validate_path("readme.md", allowed_extensions=[".txt", ".md"])
        assert result.is_valid


class TestSanitizeString:
    """Tests for sanitize_string function."""

    def test_strips_whitespace(self):
        """Test whitespace stripping."""
        result = sanitize_string("  hello  ")
        assert result == "hello"

    def test_removes_null_bytes(self):
        """Test null byte removal."""
        result = sanitize_string("hello\x00world")
        assert "\x00" not in result

    def test_escapes_html(self):
        """Test HTML escaping."""
        result = sanitize_string("<script>alert('xss')</script>")
        assert "<" not in result
        assert "&lt;" in result

    def test_escapes_quotes(self):
        """Test quote escaping."""
        result = sanitize_string('test "quoted" value')
        assert '"' not in result
        assert "&quot;" in result

    def test_allows_html_when_specified(self):
        """Test HTML allowed when specified."""
        result = sanitize_string("<b>bold</b>", allow_html=True)
        assert "<b>" in result

    def test_truncates(self):
        """Test truncation."""
        result = sanitize_string("hello world", max_length=5)
        assert len(result) == 5


class TestInputValidator:
    """Tests for InputValidator fluent interface."""

    def test_required_valid(self):
        """Test required field validation."""
        validator = InputValidator()
        result = validator.field("name", "John").required().validate()
        assert result.is_valid

    def test_required_missing(self):
        """Test required field missing."""
        validator = InputValidator()
        result = validator.field("name", None).required().validate()
        assert not result.is_valid
        assert "required" in result.error

    def test_optional_with_default(self):
        """Test optional field with default."""
        validator = InputValidator()
        result = validator.field("count", None).optional(default=10).validate()
        assert result.is_valid
        assert result.value == 10

    def test_string_validation(self):
        """Test string validation in chain."""
        validator = InputValidator()
        result = (
            validator
            .field("username", "john_doe")
            .required()
            .string(min_length=3, max_length=20)
            .validate()
        )
        assert result.is_valid

    def test_integer_validation(self):
        """Test integer validation in chain."""
        validator = InputValidator()
        result = (
            validator
            .field("age", "25")
            .required()
            .integer(minimum=0, maximum=150)
            .validate()
        )
        assert result.is_valid
        assert result.value == 25

    def test_number_validation(self):
        """Test number validation in chain."""
        validator = InputValidator()
        result = (
            validator
            .field("price", "19.99")
            .required()
            .number(minimum=0)
            .validate()
        )
        assert result.is_valid
        assert result.value == 19.99

    def test_url_validation(self):
        """Test URL validation in chain."""
        validator = InputValidator()
        result = (
            validator
            .field("website", "https://example.com")
            .required()
            .url()
            .validate()
        )
        assert result.is_valid

    def test_email_validation(self):
        """Test email validation in chain."""
        validator = InputValidator()
        result = (
            validator
            .field("email", "user@example.com")
            .required()
            .email()
            .validate()
        )
        assert result.is_valid

    def test_path_validation(self):
        """Test path validation in chain."""
        validator = InputValidator()
        result = (
            validator
            .field("file", "/home/user/file.txt")
            .required()
            .path(must_be_absolute=True)
            .validate()
        )
        assert result.is_valid

    def test_multiple_errors(self):
        """Test error accumulation doesn't occur after first error."""
        validator = InputValidator()
        result = (
            validator
            .field("age", "abc")
            .required()
            .integer(minimum=0)
            .validate()
        )
        assert not result.is_valid
        # Should have error from integer validation
        assert "integer" in result.error


class TestGenerateValidationCode:
    """Tests for validation code generation."""

    def test_generates_code(self):
        """Test code generation."""
        code = generate_validation_utilities_code()

        assert "ValidationResult" in code
        assert "validate_finite" in code
        assert "validate_string" in code
        assert "validate_integer" in code
        assert "validate_number" in code
        assert "validate_url" in code
        assert "validate_email" in code
        assert "sanitize_string" in code

    def test_generated_code_is_valid_python(self):
        """Test generated code is syntactically valid."""
        code = generate_validation_utilities_code()
        compile(code, "<generated>", "exec")
