"""Standardized input validation utilities for MCP servers.

Provides consistent validation patterns for common input types
to be used in generated MCP servers.
"""

import math
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    value: Any
    error: str | None = None

    @classmethod
    def success(cls, value: Any) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(is_valid=True, value=value, error=None)

    @classmethod
    def failure(cls, error: str, value: Any = None) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(is_valid=False, value=value, error=error)


def validate_finite(value: float | int, name: str = "value") -> ValidationResult:
    """Validate that a number is finite (not NaN or infinity).

    Args:
        value: The number to validate
        name: Name of the field for error messages

    Returns:
        ValidationResult with the validated value
    """
    if not isinstance(value, (int, float)):
        return ValidationResult.failure(f"{name} must be a number", value)

    if math.isnan(value):
        return ValidationResult.failure(f"{name} cannot be NaN", value)

    if math.isinf(value):
        return ValidationResult.failure(f"{name} cannot be infinity", value)

    return ValidationResult.success(value)


def validate_string(
    value: Any,
    name: str = "value",
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None,
    allowed_values: list[str] | None = None,
    strip: bool = True,
) -> ValidationResult:
    """Validate a string value with optional constraints.

    Args:
        value: The value to validate
        name: Name of the field for error messages
        min_length: Minimum string length
        max_length: Maximum string length
        pattern: Regex pattern to match
        allowed_values: List of allowed values (enum)
        strip: Whether to strip whitespace

    Returns:
        ValidationResult with the validated/cleaned value
    """
    if value is None:
        return ValidationResult.failure(f"{name} cannot be null", value)

    if not isinstance(value, str):
        try:
            value = str(value)
        except (ValueError, TypeError):
            return ValidationResult.failure(f"{name} must be a string", value)

    if strip:
        value = value.strip()

    if min_length is not None and len(value) < min_length:
        return ValidationResult.failure(
            f"{name} must be at least {min_length} characters", value
        )

    if max_length is not None and len(value) > max_length:
        return ValidationResult.failure(
            f"{name} must be at most {max_length} characters", value
        )

    if pattern is not None and not re.match(pattern, value):
        return ValidationResult.failure(
            f"{name} does not match required pattern", value
        )

    if allowed_values is not None and value not in allowed_values:
        return ValidationResult.failure(
            f"{name} must be one of: {', '.join(allowed_values)}", value
        )

    return ValidationResult.success(value)


def validate_integer(
    value: Any,
    name: str = "value",
    minimum: int | None = None,
    maximum: int | None = None,
    coerce: bool = True,
) -> ValidationResult:
    """Validate an integer value with optional constraints.

    Args:
        value: The value to validate
        name: Name of the field for error messages
        minimum: Minimum allowed value
        maximum: Maximum allowed value
        coerce: Whether to attempt type coercion

    Returns:
        ValidationResult with the validated value
    """
    if isinstance(value, bool):
        return ValidationResult.failure(f"{name} must be an integer, not boolean", value)

    if not isinstance(value, int):
        if coerce:
            try:
                value = int(value)
            except (ValueError, TypeError):
                return ValidationResult.failure(f"{name} must be an integer", value)
        else:
            return ValidationResult.failure(f"{name} must be an integer", value)

    if minimum is not None and value < minimum:
        return ValidationResult.failure(
            f"{name} must be at least {minimum}", value
        )

    if maximum is not None and value > maximum:
        return ValidationResult.failure(
            f"{name} must be at most {maximum}", value
        )

    return ValidationResult.success(value)


def validate_number(
    value: Any,
    name: str = "value",
    minimum: float | None = None,
    maximum: float | None = None,
    allow_infinity: bool = False,
    allow_nan: bool = False,
    coerce: bool = True,
) -> ValidationResult:
    """Validate a numeric value with optional constraints.

    Args:
        value: The value to validate
        name: Name of the field for error messages
        minimum: Minimum allowed value
        maximum: Maximum allowed value
        allow_infinity: Whether to allow infinity values
        allow_nan: Whether to allow NaN values
        coerce: Whether to attempt type coercion

    Returns:
        ValidationResult with the validated value
    """
    if isinstance(value, bool):
        return ValidationResult.failure(f"{name} must be a number, not boolean", value)

    if not isinstance(value, (int, float)):
        if coerce:
            try:
                value = float(value)
            except (ValueError, TypeError):
                return ValidationResult.failure(f"{name} must be a number", value)
        else:
            return ValidationResult.failure(f"{name} must be a number", value)

    if not allow_nan and math.isnan(value):
        return ValidationResult.failure(f"{name} cannot be NaN", value)

    if not allow_infinity and math.isinf(value):
        return ValidationResult.failure(f"{name} cannot be infinity", value)

    if minimum is not None and value < minimum:
        return ValidationResult.failure(
            f"{name} must be at least {minimum}", value
        )

    if maximum is not None and value > maximum:
        return ValidationResult.failure(
            f"{name} must be at most {maximum}", value
        )

    return ValidationResult.success(value)


def validate_url(
    value: Any,
    name: str = "url",
    allowed_schemes: list[str] | None = None,
    require_tld: bool = True,
) -> ValidationResult:
    """Validate a URL string.

    Args:
        value: The value to validate
        name: Name of the field for error messages
        allowed_schemes: List of allowed URL schemes (default: http, https)
        require_tld: Whether to require a TLD in the host

    Returns:
        ValidationResult with the validated URL
    """
    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]

    result = validate_string(value, name)
    if not result.is_valid:
        return result

    value = result.value

    try:
        parsed = urlparse(value)
    except Exception:
        return ValidationResult.failure(f"{name} is not a valid URL", value)

    if not parsed.scheme:
        return ValidationResult.failure(f"{name} must have a scheme (e.g., https://)", value)

    if parsed.scheme not in allowed_schemes:
        return ValidationResult.failure(
            f"{name} scheme must be one of: {', '.join(allowed_schemes)}", value
        )

    if not parsed.netloc:
        return ValidationResult.failure(f"{name} must have a host", value)

    # Extract host without port for TLD check
    host = parsed.netloc.split(":")[0]
    if require_tld and "." not in host and host != "localhost":
        return ValidationResult.failure(f"{name} must have a valid domain", value)

    return ValidationResult.success(value)


def validate_email(value: Any, name: str = "email") -> ValidationResult:
    """Validate an email address.

    Args:
        value: The value to validate
        name: Name of the field for error messages

    Returns:
        ValidationResult with the validated email
    """
    result = validate_string(value, name, min_length=3, max_length=254)
    if not result.is_valid:
        return result

    value = result.value

    # Basic email pattern - not RFC 5322 compliant but catches most issues
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, value):
        return ValidationResult.failure(f"{name} is not a valid email address", value)

    return ValidationResult.success(value)


def validate_path(
    value: Any,
    name: str = "path",
    must_be_absolute: bool = False,
    allowed_extensions: list[str] | None = None,
    disallow_traversal: bool = True,
) -> ValidationResult:
    """Validate a file path string.

    Args:
        value: The value to validate
        name: Name of the field for error messages
        must_be_absolute: Whether the path must be absolute
        allowed_extensions: List of allowed file extensions
        disallow_traversal: Whether to disallow path traversal (..)

    Returns:
        ValidationResult with the validated path
    """
    result = validate_string(value, name, min_length=1)
    if not result.is_valid:
        return result

    value = result.value

    # Check for path traversal attempts
    if disallow_traversal and ".." in value:
        return ValidationResult.failure(
            f"{name} cannot contain path traversal (..)", value
        )

    # Check absolute path requirement
    if must_be_absolute:
        # Works for both Unix and Windows
        is_absolute = value.startswith("/") or (len(value) > 1 and value[1] == ":")
        if not is_absolute:
            return ValidationResult.failure(f"{name} must be an absolute path", value)

    # Check file extension
    if allowed_extensions is not None:
        ext = value.rsplit(".", 1)[-1].lower() if "." in value else ""
        allowed_lower = [e.lower().lstrip(".") for e in allowed_extensions]
        if ext not in allowed_lower:
            return ValidationResult.failure(
                f"{name} must have extension: {', '.join(allowed_extensions)}", value
            )

    return ValidationResult.success(value)


def sanitize_string(
    value: str,
    allow_html: bool = False,
    max_length: int | None = None,
) -> str:
    """Sanitize a string value for safe use.

    Args:
        value: The string to sanitize
        allow_html: Whether to allow HTML tags
        max_length: Maximum length to truncate to

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        value = str(value)

    # Strip whitespace
    value = value.strip()

    # Remove null bytes
    value = value.replace("\x00", "")

    # Escape HTML if not allowed
    if not allow_html:
        value = (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    # Truncate if needed
    if max_length is not None and len(value) > max_length:
        value = value[:max_length]

    return value


class InputValidator:
    """Fluent interface for input validation.

    Example:
        validator = InputValidator()
        result = (
            validator
            .field("age", user_input)
            .required()
            .integer(minimum=0, maximum=150)
            .validate()
        )
    """

    def __init__(self):
        self._field_name: str = "value"
        self._value: Any = None
        self._errors: list[str] = []
        self._validated_value: Any = None

    def field(self, name: str, value: Any) -> "InputValidator":
        """Start validation for a field.

        Args:
            name: Field name for error messages
            value: Value to validate

        Returns:
            Self for chaining
        """
        self._field_name = name
        self._value = value
        self._validated_value = value
        self._errors = []
        return self

    def required(self) -> "InputValidator":
        """Validate that the field is not None or empty."""
        if self._value is None or self._value == "":
            self._errors.append(f"{self._field_name} is required")
        return self

    def optional(self, default: Any = None) -> "InputValidator":
        """Mark field as optional with default value."""
        if self._value is None or self._value == "":
            self._validated_value = default
        return self

    def string(
        self,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
    ) -> "InputValidator":
        """Validate as string."""
        if self._errors or self._value is None:
            return self

        result = validate_string(
            self._value,
            self._field_name,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
        )
        if not result.is_valid:
            self._errors.append(result.error)
        else:
            self._validated_value = result.value
        return self

    def integer(
        self,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> "InputValidator":
        """Validate as integer."""
        if self._errors or self._value is None:
            return self

        result = validate_integer(
            self._value,
            self._field_name,
            minimum=minimum,
            maximum=maximum,
        )
        if not result.is_valid:
            self._errors.append(result.error)
        else:
            self._validated_value = result.value
        return self

    def number(
        self,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> "InputValidator":
        """Validate as number."""
        if self._errors or self._value is None:
            return self

        result = validate_number(
            self._value,
            self._field_name,
            minimum=minimum,
            maximum=maximum,
        )
        if not result.is_valid:
            self._errors.append(result.error)
        else:
            self._validated_value = result.value
        return self

    def url(self, allowed_schemes: list[str] | None = None) -> "InputValidator":
        """Validate as URL."""
        if self._errors or self._value is None:
            return self

        result = validate_url(self._value, self._field_name, allowed_schemes)
        if not result.is_valid:
            self._errors.append(result.error)
        else:
            self._validated_value = result.value
        return self

    def email(self) -> "InputValidator":
        """Validate as email."""
        if self._errors or self._value is None:
            return self

        result = validate_email(self._value, self._field_name)
        if not result.is_valid:
            self._errors.append(result.error)
        else:
            self._validated_value = result.value
        return self

    def path(
        self,
        must_be_absolute: bool = False,
        allowed_extensions: list[str] | None = None,
    ) -> "InputValidator":
        """Validate as file path."""
        if self._errors or self._value is None:
            return self

        result = validate_path(
            self._value,
            self._field_name,
            must_be_absolute=must_be_absolute,
            allowed_extensions=allowed_extensions,
        )
        if not result.is_valid:
            self._errors.append(result.error)
        else:
            self._validated_value = result.value
        return self

    def validate(self) -> ValidationResult:
        """Complete validation and return result."""
        if self._errors:
            return ValidationResult.failure(
                "; ".join(self._errors),
                self._value,
            )
        return ValidationResult.success(self._validated_value)


def generate_validation_utilities_code() -> str:
    """Generate validation utilities code for inclusion in generated servers.

    Returns:
        Python code string with validation utilities
    """
    return '''
# ============== INPUT VALIDATION UTILITIES ==============

import math
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    value: Any
    error: str | None = None

    @classmethod
    def ok(cls, value: Any) -> "ValidationResult":
        return cls(is_valid=True, value=value, error=None)

    @classmethod
    def err(cls, error: str, value: Any = None) -> "ValidationResult":
        return cls(is_valid=False, value=value, error=error)


def validate_finite(value: float | int, name: str = "value") -> ValidationResult:
    """Validate that a number is finite (not NaN or infinity)."""
    if not isinstance(value, (int, float)):
        return ValidationResult.err(f"{name} must be a number", value)
    if math.isnan(value):
        return ValidationResult.err(f"{name} cannot be NaN", value)
    if math.isinf(value):
        return ValidationResult.err(f"{name} cannot be infinity", value)
    return ValidationResult.ok(value)


def validate_string(
    value: Any,
    name: str = "value",
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None,
) -> ValidationResult:
    """Validate a string with optional constraints."""
    if value is None:
        return ValidationResult.err(f"{name} cannot be null", value)
    if not isinstance(value, str):
        try:
            value = str(value)
        except:
            return ValidationResult.err(f"{name} must be a string", value)
    value = value.strip()
    if min_length is not None and len(value) < min_length:
        return ValidationResult.err(f"{name} must be at least {min_length} characters", value)
    if max_length is not None and len(value) > max_length:
        return ValidationResult.err(f"{name} must be at most {max_length} characters", value)
    if pattern is not None and not re.match(pattern, value):
        return ValidationResult.err(f"{name} does not match required pattern", value)
    return ValidationResult.ok(value)


def validate_integer(
    value: Any,
    name: str = "value",
    minimum: int | None = None,
    maximum: int | None = None,
) -> ValidationResult:
    """Validate an integer with optional constraints."""
    if isinstance(value, bool):
        return ValidationResult.err(f"{name} must be an integer", value)
    if not isinstance(value, int):
        try:
            value = int(value)
        except:
            return ValidationResult.err(f"{name} must be an integer", value)
    if minimum is not None and value < minimum:
        return ValidationResult.err(f"{name} must be at least {minimum}", value)
    if maximum is not None and value > maximum:
        return ValidationResult.err(f"{name} must be at most {maximum}", value)
    return ValidationResult.ok(value)


def validate_number(
    value: Any,
    name: str = "value",
    minimum: float | None = None,
    maximum: float | None = None,
) -> ValidationResult:
    """Validate a number with optional constraints."""
    if isinstance(value, bool):
        return ValidationResult.err(f"{name} must be a number", value)
    if not isinstance(value, (int, float)):
        try:
            value = float(value)
        except:
            return ValidationResult.err(f"{name} must be a number", value)
    if math.isnan(value):
        return ValidationResult.err(f"{name} cannot be NaN", value)
    if math.isinf(value):
        return ValidationResult.err(f"{name} cannot be infinity", value)
    if minimum is not None and value < minimum:
        return ValidationResult.err(f"{name} must be at least {minimum}", value)
    if maximum is not None and value > maximum:
        return ValidationResult.err(f"{name} must be at most {maximum}", value)
    return ValidationResult.ok(value)


def validate_url(value: Any, name: str = "url") -> ValidationResult:
    """Validate a URL string."""
    result = validate_string(value, name)
    if not result.is_valid:
        return result
    value = result.value
    try:
        parsed = urlparse(value)
        if not parsed.scheme or parsed.scheme not in ("http", "https"):
            return ValidationResult.err(f"{name} must use http or https", value)
        if not parsed.netloc:
            return ValidationResult.err(f"{name} must have a host", value)
    except:
        return ValidationResult.err(f"{name} is not a valid URL", value)
    return ValidationResult.ok(value)


def validate_email(value: Any, name: str = "email") -> ValidationResult:
    """Validate an email address."""
    result = validate_string(value, name, min_length=3, max_length=254)
    if not result.is_valid:
        return result
    value = result.value
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    if not re.match(pattern, value):
        return ValidationResult.err(f"{name} is not a valid email", value)
    return ValidationResult.ok(value)


def sanitize_string(value: str, max_length: int | None = None) -> str:
    """Sanitize a string for safe use."""
    if not isinstance(value, str):
        value = str(value)
    value = value.strip().replace("\\x00", "")
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    value = value.replace('"', "&quot;").replace("'", "&#x27;")
    if max_length and len(value) > max_length:
        value = value[:max_length]
    return value

'''
