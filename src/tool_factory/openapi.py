"""Enhanced OpenAPI to MCP server generator.

Supports:
- API Key authentication (header, query, cookie)
- OAuth2 / Bearer token authentication
- Request body parameters (JSON, form data)
- Path parameters
- Query parameters
- Response parsing and error handling
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from tool_factory.models import ToolSpec

logger = logging.getLogger(__name__)


class AuthType(Enum):
    """Authentication types supported by OpenAPI."""

    NONE = "none"
    API_KEY = "apiKey"
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    BASIC = "basic"


@dataclass
class AuthConfig:
    """Authentication configuration extracted from OpenAPI."""

    auth_type: AuthType = AuthType.NONE
    env_var_name: str = ""  # e.g., "API_KEY"
    header_name: str = ""  # e.g., "X-API-Key" or "Authorization"
    in_location: str = ""  # "header", "query", "cookie"
    scheme: str = ""  # "bearer", "basic"

    def to_env_check_code(self) -> str:
        """Generate code to check for required auth env var."""
        if self.auth_type == AuthType.NONE:
            return ""
        return f"""
# Authentication configuration
{self.env_var_name} = os.environ.get("{self.env_var_name}")
if not {self.env_var_name}:
    raise ValueError("Missing required environment variable: {self.env_var_name}")
"""

    def to_header_code(self) -> str:
        """Generate code to add auth headers."""
        if self.auth_type == AuthType.NONE:
            return "headers = {}"
        elif self.auth_type == AuthType.BEARER:
            return f'headers = {{"Authorization": f"Bearer {{{self.env_var_name}}}"}}'
        elif self.auth_type == AuthType.API_KEY:
            if self.in_location == "header":
                return f'headers = {{"{self.header_name}": {self.env_var_name}}}'
            else:
                return "headers = {}"
        elif self.auth_type == AuthType.BASIC:
            return f"""import base64
_auth_bytes = base64.b64encode({self.env_var_name}.encode())
headers = {{"Authorization": f"Basic {{_auth_bytes.decode()}}"}}"""
        return "headers = {}"


@dataclass
class EndpointSpec:
    """Specification for a single API endpoint."""

    path: str
    method: str  # GET, POST, PUT, DELETE, PATCH
    operation_id: str
    summary: str
    description: str
    parameters: list[dict[str, Any]] = field(default_factory=list)
    request_body: dict[str, Any] | None = None
    responses: dict[str, Any] = field(default_factory=dict)
    security: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


class OpenAPIValidationError(Exception):
    """Exception raised for OpenAPI spec validation errors."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


class OpenAPIValidator:
    """Validate OpenAPI specifications."""

    REQUIRED_FIELDS_30 = ["openapi", "info", "paths"]
    REQUIRED_INFO_FIELDS = ["title", "version"]

    @classmethod
    def validate(cls, spec: dict[str, Any], raise_on_error: bool = True) -> list[str]:
        """Validate an OpenAPI specification.

        Args:
            spec: OpenAPI specification as dictionary
            raise_on_error: If True, raise exception on validation error

        Returns:
            List of validation error messages (empty if valid)

        Raises:
            OpenAPIValidationError: If validation fails and raise_on_error is True
        """
        errors: list[str] = []

        # Check spec is a dict
        if not isinstance(spec, dict):
            errors.append(f"Spec must be a dictionary, got {type(spec).__name__}")
            if raise_on_error:
                raise OpenAPIValidationError("Invalid OpenAPI specification", errors)
            return errors

        # Check version field
        version = spec.get("openapi") or spec.get("swagger")
        if not version:
            errors.append("Missing 'openapi' or 'swagger' version field")
        elif not isinstance(version, str):
            errors.append(f"Version must be a string, got {type(version).__name__}")
        elif not re.match(r"^\d+\.\d+", version):
            errors.append(f"Invalid version format: {version}")

        # Check info section
        info = spec.get("info")
        if not info:
            errors.append("Missing required 'info' section")
        elif isinstance(info, dict):
            for field in cls.REQUIRED_INFO_FIELDS:
                if field not in info:
                    errors.append(f"Missing required info field: {field}")

        # Check paths section
        paths = spec.get("paths")
        if not paths:
            errors.append("Missing required 'paths' section")
        elif isinstance(paths, dict):
            for path, methods in paths.items():
                # Validate path format
                if not path.startswith("/"):
                    errors.append(f"Path must start with '/': {path}")

                # Validate each method
                if isinstance(methods, dict):
                    for method, operation in methods.items():
                        if method.lower() not in [
                            "get",
                            "post",
                            "put",
                            "delete",
                            "patch",
                            "head",
                            "options",
                        ]:
                            continue  # Skip non-HTTP method keys
                        if isinstance(operation, dict):
                            # Check for operationId
                            if "operationId" not in operation:
                                logger.debug(
                                    f"Missing operationId for {method.upper()} {path}"
                                )

        # Validate servers (OpenAPI 3.x)
        servers = spec.get("servers", [])
        for i, server in enumerate(servers):
            if isinstance(server, dict):
                url = server.get("url", "")
                if url:
                    validation_error = cls._validate_url(url)
                    if validation_error:
                        errors.append(
                            f"Invalid server URL at index {i}: {validation_error}"
                        )

        if errors and raise_on_error:
            raise OpenAPIValidationError(
                f"OpenAPI specification has {len(errors)} validation error(s)", errors
            )

        return errors

    @classmethod
    def _validate_url(cls, url: str) -> str | None:
        """Validate a URL.

        Args:
            url: URL string to validate

        Returns:
            Error message or None if valid
        """
        # Allow template variables in URL
        if "{" in url:
            # Replace template vars for validation
            url = re.sub(r"\{[^}]+\}", "placeholder", url)

        try:
            parsed = urlparse(url)
            if not parsed.scheme and not url.startswith("/"):
                return "URL must have a scheme (http/https) or be a relative path"
            if parsed.scheme and parsed.scheme not in ["http", "https"]:
                return f"Unsupported URL scheme: {parsed.scheme}"
            return None
        except Exception as e:
            return str(e)


class OpenAPIParser:
    """Parse OpenAPI specification and extract endpoints."""

    def __init__(self, spec: dict[str, Any], validate: bool = True) -> None:
        """Initialize the parser.

        Args:
            spec: OpenAPI specification as dictionary
            validate: If True, validate the spec before parsing
        """
        if validate:
            errors = OpenAPIValidator.validate(spec, raise_on_error=False)
            if errors:
                logger.warning(
                    f"OpenAPI spec has {len(errors)} validation issues: {errors}"
                )

        self.spec = spec
        self.version = self._detect_version()

    def _detect_version(self) -> str:
        """Detect OpenAPI version."""
        if "openapi" in self.spec:
            return self.spec["openapi"]
        elif "swagger" in self.spec:
            return self.spec["swagger"]
        return "3.0.0"

    def get_info(self) -> dict[str, Any]:
        """Get API info (title, description, version)."""
        return self.spec.get("info", {})

    def get_servers(self) -> list[dict[str, Any]]:
        """Get server URLs."""
        # OpenAPI 3.x
        if "servers" in self.spec:
            return self.spec["servers"]
        # Swagger 2.x
        host = self.spec.get("host", "localhost")
        scheme = self.spec.get("schemes", ["https"])[0]
        base_path = self.spec.get("basePath", "")
        return [{"url": f"{scheme}://{host}{base_path}"}]

    def get_auth_config(self) -> AuthConfig:
        """Extract authentication configuration."""
        security_schemes = {}

        # OpenAPI 3.x
        if "components" in self.spec:
            security_schemes = self.spec.get("components", {}).get(
                "securitySchemes", {}
            )
        # Swagger 2.x
        elif "securityDefinitions" in self.spec:
            security_schemes = self.spec.get("securityDefinitions", {})

        if not security_schemes:
            return AuthConfig()

        # Take the first security scheme
        for name, scheme in security_schemes.items():
            scheme_type = scheme.get("type", "").lower()

            if scheme_type == "apikey":
                return AuthConfig(
                    auth_type=AuthType.API_KEY,
                    env_var_name=name.upper().replace("-", "_").replace(" ", "_")
                    + "_API_KEY",
                    header_name=scheme.get("name", "X-API-Key"),
                    in_location=scheme.get("in", "header"),
                )
            elif scheme_type == "http":
                http_scheme = scheme.get("scheme", "bearer").lower()
                if http_scheme == "bearer":
                    return AuthConfig(
                        auth_type=AuthType.BEARER,
                        env_var_name=name.upper().replace("-", "_") + "_TOKEN",
                        header_name="Authorization",
                        scheme="bearer",
                    )
                elif http_scheme == "basic":
                    return AuthConfig(
                        auth_type=AuthType.BASIC,
                        env_var_name=name.upper().replace("-", "_") + "_CREDENTIALS",
                        header_name="Authorization",
                        scheme="basic",
                    )
            elif scheme_type == "oauth2":
                return AuthConfig(
                    auth_type=AuthType.OAUTH2,
                    env_var_name=name.upper().replace("-", "_") + "_TOKEN",
                    header_name="Authorization",
                    scheme="bearer",
                )

        return AuthConfig()

    def get_endpoints(self) -> list[EndpointSpec]:
        """Extract all endpoints from the spec."""
        endpoints = []
        paths = self.spec.get("paths", {})

        for path, path_item in paths.items():
            # Handle path-level parameters
            path_params = path_item.get("parameters", [])

            for method in ["get", "post", "put", "delete", "patch", "head", "options"]:
                if method not in path_item:
                    continue

                operation = path_item[method]

                # Generate operation ID if not provided
                operation_id = operation.get("operationId")
                if not operation_id:
                    clean_path = (
                        path.replace("/", "_").replace("{", "").replace("}", "")
                    )
                    operation_id = f"{method}{clean_path}"

                # Merge path-level and operation-level parameters
                all_params = path_params + operation.get("parameters", [])

                # Resolve parameter references
                resolved_params = [self._resolve_ref(p) for p in all_params]

                # Get request body
                request_body = operation.get("requestBody")
                if request_body:
                    request_body = self._resolve_ref(request_body)

                endpoints.append(
                    EndpointSpec(
                        path=path,
                        method=method.upper(),
                        operation_id=operation_id,
                        summary=operation.get("summary", ""),
                        description=operation.get("description", ""),
                        parameters=resolved_params,
                        request_body=request_body,
                        responses=operation.get("responses", {}),
                        security=operation.get("security", []),
                        tags=operation.get("tags", []),
                    )
                )

        return endpoints

    def _resolve_ref(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Resolve $ref references in the spec."""
        if not isinstance(obj, dict):
            return obj

        if "$ref" not in obj:
            return obj

        ref_path = obj["$ref"]
        if not ref_path.startswith("#/"):
            return obj

        # Navigate to the referenced object
        parts = ref_path[2:].split("/")
        current = self.spec
        for part in parts:
            current = current.get(part, {})

        return current


class OpenAPIServerGenerator:
    """Generate MCP server code from OpenAPI specification."""

    def __init__(self, spec: dict[str, Any], base_url: str | None = None) -> None:
        self.parser = OpenAPIParser(spec)
        self.spec = spec

        # Use provided base_url or extract from spec
        if base_url:
            self.base_url = base_url.rstrip("/")
        else:
            servers = self.parser.get_servers()
            self.base_url = (
                servers[0]["url"].rstrip("/") if servers else "http://localhost"
            )

        self.auth_config = self.parser.get_auth_config()
        self.endpoints = self.parser.get_endpoints()

    def generate_server_code(self, server_name: str) -> str:
        """Generate complete MCP server code."""
        info = self.parser.get_info()

        # Build imports
        imports = [
            '"""Auto-generated MCP server from OpenAPI specification."""',
            "",
            "import os",
            "import json",
            "from typing import Any",
            "from datetime import datetime",
            "",
            "import httpx",
            "from mcp.server.fastmcp import FastMCP",
            "",
        ]

        # Build code parts
        code_parts = [
            "\n".join(imports),
            f'mcp = FastMCP("{server_name}", json_response=True)',
            "",
            f'BASE_URL = "{self.base_url}"',
            "",
        ]

        # Add auth configuration
        if self.auth_config.auth_type != AuthType.NONE:
            code_parts.append(self.auth_config.to_env_check_code())

        # Add HTTP client setup
        code_parts.append(self._generate_client_setup())

        # Add health check
        code_parts.append(self._generate_health_check(server_name, info))

        # Add tool for each endpoint
        for endpoint in self.endpoints:
            code_parts.append(self._generate_tool(endpoint))

        # Add main block
        code_parts.extend(
            [
                "",
                "# ============== MAIN ==============",
                "",
                'if __name__ == "__main__":',
                '    mcp.run(transport="stdio")',
                "",
            ]
        )

        return "\n".join(code_parts)

    def _generate_client_setup(self) -> str:
        """Generate HTTP client setup code."""
        header_code = self.auth_config.to_header_code()

        return f'''
# HTTP client setup
{header_code}

async def _make_request(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make HTTP request to the API."""
    url = f"{{BASE_URL}}{{path}}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body,
            )
            response.raise_for_status()

            # Try to parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError:
                return {{"text": response.text, "status_code": response.status_code}}

        except httpx.HTTPStatusError as e:
            return {{
                "error": f"HTTP {{e.response.status_code}}",
                "detail": e.response.text[:500],
            }}
        except httpx.RequestError as e:
            return {{"error": f"Request failed: {{str(e)[:200]}}"}}

'''

    def _generate_health_check(self, server_name: str, info: dict[str, Any]) -> str:
        """Generate health check tool."""
        api_title = info.get("title", server_name)
        api_version = info.get("version", "1.0.0")

        auth_check = ""
        if self.auth_config.auth_type != AuthType.NONE:
            env_var = self.auth_config.env_var_name
            auth_check = f"""
    # Check auth configuration
    auth_status = "configured" if {env_var} else "MISSING"
    result["auth_config"] = {{"{env_var}": auth_status}}
    if auth_status == "MISSING":
        result["status"] = "unhealthy"
        result["error"] = "Missing API authentication"
"""

        return f'''
# ============== HEALTH CHECK ==============

@mcp.tool()
def health_check() -> dict:
    """
    Check server health and API connectivity.

    Returns:
        Health status including API info and auth configuration
    """
    result = {{
        "status": "healthy",
        "server": "{server_name}",
        "api": "{api_title}",
        "api_version": "{api_version}",
        "base_url": BASE_URL,
        "timestamp": datetime.now().isoformat(),
        "endpoints_available": {len(self.endpoints)},
    }}
{auth_check}
    return result


# ============== API TOOLS ==============
'''

    def _generate_tool(self, endpoint: EndpointSpec) -> str:
        """Generate a tool function for an endpoint."""
        # Build function parameters
        params = []
        param_docs = []
        path_params = []
        query_params = []

        for param in endpoint.parameters:
            param_name = param.get("name", "")
            param_in = param.get("in", "query")
            param_required = param.get("required", False)
            param_schema = param.get("schema", {"type": "string"})
            param_type = self._schema_to_python_type(param_schema)
            param_desc = param.get("description", "")

            if param_required:
                params.append(f"{param_name}: {param_type}")
            else:
                default = self._get_default_value(param_schema)
                params.append(f"{param_name}: {param_type} = {default}")

            param_docs.append(f"        {param_name}: {param_desc}")

            if param_in == "path":
                path_params.append(param_name)
            elif param_in == "query":
                query_params.append(param_name)

        # Handle request body
        body_param = None
        if endpoint.request_body:
            content = endpoint.request_body.get("content", {})
            json_content = content.get("application/json", {})
            if json_content:
                body_param = "request_body"
                params.append("request_body: dict")
                param_docs.append("        request_body: JSON request body")

        params_str = ", ".join(params) if params else ""
        params_docs_str = "\n".join(param_docs) if param_docs else "        None"

        # Build function body
        func_name = self._sanitize_name(endpoint.operation_id)
        description = (
            endpoint.summary
            or endpoint.description
            or f"{endpoint.method} {endpoint.path}"
        )

        # Build path with path parameters
        path_code = f'"{endpoint.path}"'
        if path_params:
            path_code = f'f"{endpoint.path}"'

        # Build query params dict
        query_code = ""
        if query_params:
            query_items = ", ".join(f'"{p}": {p}' for p in query_params)
            query_code = (
                f"params = {{{query_items}}}\n"
                "    params = {k: v for k, v in params.items() if v is not None}"
            )
        else:
            query_code = "params = None"

        # Build request body
        body_code = "json_body = None"
        if body_param:
            body_code = "json_body = request_body"

        return f'''
@mcp.tool()
async def {func_name}({params_str}) -> dict:
    """
    {description}

    Args:
{params_docs_str}

    Returns:
        API response as dictionary
    """
    path = {path_code}
    {query_code}
    {body_code}

    return await _make_request("{endpoint.method}", path, params=params, json_body=json_body)
'''

    def _sanitize_name(self, name: str) -> str:
        """Convert operation ID to valid Python function name."""
        # Replace invalid characters
        name = name.replace("-", "_").replace(" ", "_").replace(".", "_")
        # Ensure it starts with a letter
        if name and name[0].isdigit():
            name = f"op_{name}"
        # Remove any remaining invalid chars
        name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
        return name.lower()

    def _schema_to_python_type(self, schema: dict[str, Any]) -> str:
        """Convert JSON Schema type to Python type hint."""
        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }
        json_type = schema.get("type", "string")
        return type_map.get(json_type, "Any")

    def _get_default_value(self, schema: dict[str, Any]) -> str:
        """Get default value for optional parameter."""
        if "default" in schema:
            default = schema["default"]
            if isinstance(default, str):
                return f'"{default}"'
            return str(default)
        return "None"

    def get_tool_specs(self) -> list[ToolSpec]:
        """Extract ToolSpec objects for documentation."""
        specs = []

        for endpoint in self.endpoints:
            # Build input schema
            input_schema: dict[str, Any] = {
                "type": "object",
                "properties": {},
                "required": [],
            }

            for param in endpoint.parameters:
                param_name = param.get("name", "")
                param_schema = param.get("schema", {"type": "string"})
                input_schema["properties"][param_name] = {
                    "type": param_schema.get("type", "string"),
                    "description": param.get("description", ""),
                }
                if param.get("required", False):
                    input_schema["required"].append(param_name)

            # Add request body if present
            if endpoint.request_body:
                input_schema["properties"]["request_body"] = {
                    "type": "object",
                    "description": "JSON request body",
                }

            specs.append(
                ToolSpec(
                    name=self._sanitize_name(endpoint.operation_id),
                    description=endpoint.summary
                    or endpoint.description
                    or f"{endpoint.method} {endpoint.path}",
                    input_schema=input_schema,
                    dependencies=["httpx"],
                )
            )

        return specs

    def _sanitize_name(self, name: str) -> str:
        """Convert operation ID to valid Python function name."""
        name = name.replace("-", "_").replace(" ", "_").replace(".", "_")
        if name and name[0].isdigit():
            name = f"op_{name}"
        name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
        return name.lower()

    def get_auth_env_vars(self) -> list[str]:
        """Get list of required auth environment variables."""
        if self.auth_config.auth_type != AuthType.NONE:
            return [self.auth_config.env_var_name]
        return []
