"""Request/Response validation middleware for MCP servers.

Provides validation based on JSON Schema (from OpenAPI specs) with
Pydantic integration for strong typing and coercion.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when request or response validation fails."""

    def __init__(
        self,
        message: str,
        errors: list[dict[str, Any]] | None = None,
        field_path: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.errors = errors or []
        self.field_path = field_path

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error": "Validation Error",
            "message": self.message,
            "details": self.errors,
            "field": self.field_path,
        }


class ValidationType(Enum):
    """Types of validation to perform."""

    REQUEST = "request"
    RESPONSE = "response"
    BOTH = "both"


@dataclass
class SchemaValidator:
    """JSON Schema validator with type coercion support.

    Validates values against JSON Schema definitions from OpenAPI specs.
    """

    schema: dict[str, Any]
    coerce_types: bool = True

    def validate(self, value: Any) -> tuple[bool, Any, list[str]]:
        """Validate a value against the schema.

        Args:
            value: Value to validate

        Returns:
            Tuple of (is_valid, coerced_value, errors)
        """
        errors: list[str] = []
        coerced = value

        schema_type = self.schema.get("type")

        if schema_type == "object":
            coerced, obj_errors = self._validate_object(value)
            errors.extend(obj_errors)
        elif schema_type == "array":
            coerced, arr_errors = self._validate_array(value)
            errors.extend(arr_errors)
        elif schema_type == "string":
            coerced, str_errors = self._validate_string(value)
            errors.extend(str_errors)
        elif schema_type == "integer":
            coerced, int_errors = self._validate_integer(value)
            errors.extend(int_errors)
        elif schema_type == "number":
            coerced, num_errors = self._validate_number(value)
            errors.extend(num_errors)
        elif schema_type == "boolean":
            coerced, bool_errors = self._validate_boolean(value)
            errors.extend(bool_errors)
        elif schema_type is None and "anyOf" in self.schema:
            coerced, anyof_errors = self._validate_anyof(value)
            errors.extend(anyof_errors)

        return len(errors) == 0, coerced, errors

    def _validate_object(self, value: Any) -> tuple[Any, list[str]]:
        """Validate object type."""
        errors: list[str] = []

        if not isinstance(value, dict):
            if self.coerce_types and value is None:
                return {}, []
            return value, ["Expected object type"]

        result = dict(value)
        properties = self.schema.get("properties", {})
        required = self.schema.get("required", [])

        # Check required fields
        for req_field in required:
            if req_field not in value:
                errors.append(f"Missing required field: {req_field}")

        # Validate each property
        for prop_name, prop_schema in properties.items():
            if prop_name in value:
                prop_validator = SchemaValidator(prop_schema, self.coerce_types)
                is_valid, coerced_val, prop_errors = prop_validator.validate(
                    value[prop_name]
                )
                if not is_valid:
                    errors.extend([f"{prop_name}: {e}" for e in prop_errors])
                else:
                    result[prop_name] = coerced_val

        # Check additionalProperties if specified
        additional = self.schema.get("additionalProperties")
        if additional is False:
            allowed = set(properties.keys())
            extra = set(value.keys()) - allowed
            if extra:
                errors.append(f"Additional properties not allowed: {extra}")

        return result, errors

    def _validate_array(self, value: Any) -> tuple[Any, list[str]]:
        """Validate array type."""
        errors: list[str] = []

        if not isinstance(value, list):
            if self.coerce_types:
                if value is None:
                    return [], []
                return [value], []
            return value, ["Expected array type"]

        result = []
        items_schema = self.schema.get("items", {})
        item_validator = SchemaValidator(items_schema, self.coerce_types)

        for i, item in enumerate(value):
            is_valid, coerced_item, item_errors = item_validator.validate(item)
            if not is_valid:
                errors.extend([f"[{i}]: {e}" for e in item_errors])
            result.append(coerced_item)

        # Check array constraints
        min_items = self.schema.get("minItems")
        max_items = self.schema.get("maxItems")

        if min_items is not None and len(result) < min_items:
            errors.append(f"Array has {len(result)} items, minimum is {min_items}")
        if max_items is not None and len(result) > max_items:
            errors.append(f"Array has {len(result)} items, maximum is {max_items}")

        return result, errors

    def _validate_string(self, value: Any) -> tuple[Any, list[str]]:
        """Validate string type."""
        errors: list[str] = []

        if not isinstance(value, str):
            if self.coerce_types and value is not None:
                value = str(value)
            elif value is None:
                return None, (
                    [] if not self.schema.get("required") else ["Value cannot be null"]
                )
            else:
                return value, ["Expected string type"]

        # Check string constraints
        min_length = self.schema.get("minLength")
        max_length = self.schema.get("maxLength")
        pattern = self.schema.get("pattern")
        enum_values = self.schema.get("enum")

        if min_length is not None and len(value) < min_length:
            errors.append(f"String too short, minimum length is {min_length}")
        if max_length is not None and len(value) > max_length:
            errors.append(f"String too long, maximum length is {max_length}")

        if pattern:
            import re

            if not re.match(pattern, value):
                errors.append(f"String does not match pattern: {pattern}")

        if enum_values and value not in enum_values:
            errors.append(f"Value must be one of: {enum_values}")

        return value, errors

    def _validate_integer(self, value: Any) -> tuple[Any, list[str]]:
        """Validate integer type."""
        errors: list[str] = []

        if isinstance(value, bool):
            # bool is a subclass of int in Python, handle separately
            return value, ["Expected integer, got boolean"]

        if not isinstance(value, int):
            if self.coerce_types:
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    return value, ["Cannot convert to integer"]
            else:
                return value, ["Expected integer type"]

        errors.extend(self._check_numeric_constraints(value))
        return value, errors

    def _validate_number(self, value: Any) -> tuple[Any, list[str]]:
        """Validate number type."""
        errors: list[str] = []

        if isinstance(value, bool):
            return value, ["Expected number, got boolean"]

        if not isinstance(value, (int, float)):
            if self.coerce_types:
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    return value, ["Cannot convert to number"]
            else:
                return value, ["Expected number type"]

        # Check for NaN/Infinity
        import math

        if math.isnan(value) or math.isinf(value):
            errors.append("Value must be finite")

        errors.extend(self._check_numeric_constraints(value))
        return value, errors

    def _validate_boolean(self, value: Any) -> tuple[Any, list[str]]:
        """Validate boolean type."""
        if isinstance(value, bool):
            return value, []

        if self.coerce_types:
            # Common boolean coercions
            if value in (1, "1", "true", "True", "yes", "Yes"):
                return True, []
            if value in (0, "0", "false", "False", "no", "No"):
                return False, []

        return value, ["Expected boolean type"]

    def _validate_anyof(self, value: Any) -> tuple[Any, list[str]]:
        """Validate anyOf schema."""
        any_of = self.schema.get("anyOf", [])

        for sub_schema in any_of:
            validator = SchemaValidator(sub_schema, self.coerce_types)
            is_valid, coerced, _ = validator.validate(value)
            if is_valid:
                return coerced, []

        return value, ["Value does not match any of the allowed schemas"]

    def _check_numeric_constraints(self, value: int | float) -> list[str]:
        """Check numeric constraints (min, max, etc.)."""
        errors = []

        minimum = self.schema.get("minimum")
        maximum = self.schema.get("maximum")
        exclusive_min = self.schema.get("exclusiveMinimum")
        exclusive_max = self.schema.get("exclusiveMaximum")
        multiple_of = self.schema.get("multipleOf")

        if minimum is not None and value < minimum:
            errors.append(f"Value {value} is less than minimum {minimum}")
        if maximum is not None and value > maximum:
            errors.append(f"Value {value} is greater than maximum {maximum}")
        if exclusive_min is not None and value <= exclusive_min:
            errors.append(f"Value {value} must be greater than {exclusive_min}")
        if exclusive_max is not None and value >= exclusive_max:
            errors.append(f"Value {value} must be less than {exclusive_max}")
        if multiple_of is not None and value % multiple_of != 0:
            errors.append(f"Value {value} is not a multiple of {multiple_of}")

        return errors


@dataclass
class RequestValidator:
    """Validates incoming tool requests against schemas."""

    schemas: dict[str, dict[str, Any]] = field(default_factory=dict)
    coerce_types: bool = True
    strict_mode: bool = False

    def add_schema(self, tool_name: str, schema: dict[str, Any]) -> None:
        """Register a schema for a tool.

        Args:
            tool_name: Name of the tool
            schema: JSON Schema for the tool's input
        """
        self.schemas[tool_name] = schema

    def validate(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> tuple[bool, dict[str, Any], list[str]]:
        """Validate request arguments against schema.

        Args:
            tool_name: Name of the tool being called
            arguments: Arguments provided to the tool

        Returns:
            Tuple of (is_valid, coerced_arguments, errors)
        """
        if tool_name not in self.schemas:
            if self.strict_mode:
                return False, arguments, [f"No schema registered for tool: {tool_name}"]
            return True, arguments, []

        schema = self.schemas[tool_name]
        validator = SchemaValidator(schema, self.coerce_types)
        return validator.validate(arguments)


@dataclass
class ResponseValidator:
    """Validates tool responses against schemas."""

    schemas: dict[str, dict[str, Any]] = field(default_factory=dict)
    log_warnings: bool = True

    def add_schema(self, tool_name: str, schema: dict[str, Any]) -> None:
        """Register a response schema for a tool.

        Args:
            tool_name: Name of the tool
            schema: JSON Schema for the tool's response
        """
        self.schemas[tool_name] = schema

    def validate(
        self,
        tool_name: str,
        response: Any,
    ) -> tuple[bool, list[str]]:
        """Validate response against schema.

        Args:
            tool_name: Name of the tool that produced the response
            response: The response to validate

        Returns:
            Tuple of (is_valid, errors)
        """
        if tool_name not in self.schemas:
            return True, []

        schema = self.schemas[tool_name]
        validator = SchemaValidator(
            schema, coerce_types=False
        )  # Don't coerce responses
        is_valid, _, errors = validator.validate(response)

        if not is_valid and self.log_warnings:
            logger.warning(f"Response validation failed for {tool_name}: {errors}")

        return is_valid, errors


@dataclass
class ValidationMiddleware:
    """Middleware that validates requests and responses.

    Can be used as a decorator or wrapper for tool functions.
    """

    request_validator: RequestValidator = field(default_factory=RequestValidator)
    response_validator: ResponseValidator = field(default_factory=ResponseValidator)
    validation_type: ValidationType = ValidationType.REQUEST
    raise_on_request_error: bool = True
    raise_on_response_error: bool = False

    def register_tool(
        self,
        tool_name: str,
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
    ) -> None:
        """Register schemas for a tool.

        Args:
            tool_name: Name of the tool
            input_schema: JSON Schema for input validation
            output_schema: JSON Schema for output validation
        """
        if input_schema:
            self.request_validator.add_schema(tool_name, input_schema)
        if output_schema:
            self.response_validator.add_schema(tool_name, output_schema)

    def wrap(self, tool_name: str) -> Callable:
        """Create a decorator for a tool function.

        Args:
            tool_name: Name of the tool

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs) -> Any:
                # Validate request
                if self.validation_type in (
                    ValidationType.REQUEST,
                    ValidationType.BOTH,
                ):
                    is_valid, coerced, errors = self.request_validator.validate(
                        tool_name, kwargs
                    )
                    if not is_valid:
                        if self.raise_on_request_error:
                            raise ValidationError(
                                f"Request validation failed for {tool_name}",
                                errors=[{"error": e} for e in errors],
                            )
                        logger.warning(
                            f"Request validation errors for {tool_name}: {errors}"
                        )
                    else:
                        kwargs = coerced

                # Call the function
                result = func(*args, **kwargs)

                # Validate response
                if self.validation_type in (
                    ValidationType.RESPONSE,
                    ValidationType.BOTH,
                ):
                    is_valid, errors = self.response_validator.validate(
                        tool_name, result
                    )
                    if not is_valid and self.raise_on_response_error:
                        raise ValidationError(
                            f"Response validation failed for {tool_name}",
                            errors=[{"error": e} for e in errors],
                        )

                return result

            return wrapper

        return decorator

    @classmethod
    def from_openapi(
        cls,
        openapi_spec: dict[str, Any],
        validation_type: ValidationType = ValidationType.REQUEST,
    ) -> "ValidationMiddleware":
        """Create middleware from an OpenAPI specification.

        Args:
            openapi_spec: OpenAPI specification dict
            validation_type: Type of validation to perform

        Returns:
            Configured ValidationMiddleware instance
        """
        middleware = cls(validation_type=validation_type)

        paths = openapi_spec.get("paths", {})
        components = openapi_spec.get("components", {})
        schemas = components.get("schemas", {})

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ("get", "post", "put", "patch", "delete"):
                    continue

                operation_id = operation.get("operationId")
                if not operation_id:
                    continue

                # Extract input schema from request body
                request_body = operation.get("requestBody", {})
                content = request_body.get("content", {})
                json_content = content.get("application/json", {})
                input_schema = json_content.get("schema")

                # Resolve $ref if present
                if input_schema and "$ref" in input_schema:
                    ref = input_schema["$ref"]
                    if ref.startswith("#/components/schemas/"):
                        schema_name = ref.split("/")[-1]
                        input_schema = schemas.get(schema_name)

                # Extract output schema from responses
                responses = operation.get("responses", {})
                success_response = responses.get("200", responses.get("201", {}))
                resp_content = success_response.get("content", {})
                resp_json = resp_content.get("application/json", {})
                output_schema = resp_json.get("schema")

                # Resolve $ref for output
                if output_schema and "$ref" in output_schema:
                    ref = output_schema["$ref"]
                    if ref.startswith("#/components/schemas/"):
                        schema_name = ref.split("/")[-1]
                        output_schema = schemas.get(schema_name)

                middleware.register_tool(operation_id, input_schema, output_schema)

        return middleware


def generate_validation_middleware_code(tool_specs: list[dict[str, Any]]) -> str:
    """Generate validation middleware code for tool specs.

    Args:
        tool_specs: List of tool specifications with input_schema

    Returns:
        Python code string for validation middleware
    """
    code_parts = [
        '''
# ============== REQUEST/RESPONSE VALIDATION ==============

from dataclasses import dataclass, field
from typing import Any, Callable
import logging
import math
import re

validation_logger = logging.getLogger("mcp_server.validation")


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, message: str, errors: list[dict] | None = None):
        super().__init__(message)
        self.message = message
        self.errors = errors or []

    def to_dict(self) -> dict:
        return {"error": "Validation Error", "message": self.message, "details": self.errors}


def validate_schema(value: Any, schema: dict, coerce: bool = True) -> tuple[bool, Any, list[str]]:
    """Validate value against JSON Schema."""
    errors = []
    coerced = value
    schema_type = schema.get("type")

    if schema_type == "object":
        if not isinstance(value, dict):
            return (False, value, ["Expected object"]) if not coerce else (True, {}, [])
        coerced = dict(value)
        for prop, prop_schema in schema.get("properties", {}).items():
            if prop in value:
                ok, c, errs = validate_schema(value[prop], prop_schema, coerce)
                if not ok:
                    errors.extend([f"{prop}: {e}" for e in errs])
                coerced[prop] = c
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"Missing required: {req}")

    elif schema_type == "array":
        if not isinstance(value, list):
            return (False, value, ["Expected array"]) if not coerce else (True, [], [])
        coerced = []
        for i, item in enumerate(value):
            ok, c, errs = validate_schema(item, schema.get("items", {}), coerce)
            if not ok:
                errors.extend([f"[{i}]: {e}" for e in errs])
            coerced.append(c)

    elif schema_type == "string":
        if not isinstance(value, str) and coerce and value is not None:
            coerced = str(value)
        elif not isinstance(value, str):
            return False, value, ["Expected string"]
        if "minLength" in schema and len(coerced) < schema["minLength"]:
            errors.append(f"String too short (min {schema['minLength']})")
        if "maxLength" in schema and len(coerced) > schema["maxLength"]:
            errors.append(f"String too long (max {schema['maxLength']})")
        if "pattern" in schema and not re.match(schema["pattern"], coerced):
            errors.append(f"Does not match pattern")
        if "enum" in schema and coerced not in schema["enum"]:
            errors.append(f"Must be one of {schema['enum']}")

    elif schema_type == "integer":
        if isinstance(value, bool):
            return False, value, ["Expected integer, got boolean"]
        if not isinstance(value, int):
            if coerce:
                try:
                    coerced = int(value)
                except (ValueError, TypeError):
                    return False, value, ["Cannot convert to integer"]
            else:
                return False, value, ["Expected integer"]
        if "minimum" in schema and coerced < schema["minimum"]:
            errors.append(f"Value below minimum {schema['minimum']}")
        if "maximum" in schema and coerced > schema["maximum"]:
            errors.append(f"Value above maximum {schema['maximum']}")

    elif schema_type == "number":
        if isinstance(value, bool):
            return False, value, ["Expected number, got boolean"]
        if not isinstance(value, (int, float)):
            if coerce:
                try:
                    coerced = float(value)
                except (ValueError, TypeError):
                    return False, value, ["Cannot convert to number"]
            else:
                return False, value, ["Expected number"]
        if not math.isfinite(coerced):
            errors.append("Value must be finite")
        if "minimum" in schema and coerced < schema["minimum"]:
            errors.append(f"Value below minimum {schema['minimum']}")
        if "maximum" in schema and coerced > schema["maximum"]:
            errors.append(f"Value above maximum {schema['maximum']}")

    elif schema_type == "boolean":
        if not isinstance(value, bool):
            if coerce:
                if value in (1, "1", "true", "True", "yes"):
                    coerced = True
                elif value in (0, "0", "false", "False", "no"):
                    coerced = False
                else:
                    return False, value, ["Expected boolean"]
            else:
                return False, value, ["Expected boolean"]

    return len(errors) == 0, coerced, errors


# Tool input schemas for validation
TOOL_SCHEMAS: dict[str, dict] = {
'''
    ]

    # Add schemas for each tool
    for tool in tool_specs:
        tool_name = tool.get("name", "unknown")
        input_schema = tool.get("input_schema", tool.get("inputSchema", {}))
        code_parts.append(f'    "{tool_name}": {repr(input_schema)},')

    code_parts.append(
        '''}


def validate_tool_input(tool_name: str, arguments: dict) -> dict:
    """Validate and coerce tool input arguments.

    Args:
        tool_name: Name of the tool
        arguments: Input arguments

    Returns:
        Coerced arguments

    Raises:
        ValidationError: If validation fails
    """
    schema = TOOL_SCHEMAS.get(tool_name)
    if not schema:
        return arguments

    is_valid, coerced, errors = validate_schema(arguments, schema)
    if not is_valid:
        raise ValidationError(
            f"Invalid input for {tool_name}",
            errors=[{"field": e.split(":")[0] if ":" in e else None, "error": e} for e in errors]
        )

    return coerced


def with_validation(tool_name: str):
    """Decorator to add input validation to a tool function."""
    def decorator(func: Callable) -> Callable:
        def wrapper(**kwargs) -> Any:
            validated = validate_tool_input(tool_name, kwargs)
            return func(**validated)
        return wrapper
    return decorator

'''
    )

    return "\n".join(code_parts)
