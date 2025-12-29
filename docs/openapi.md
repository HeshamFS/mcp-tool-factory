# OpenAPI Integration

Generate MCP servers from OpenAPI specifications. This guide covers importing REST APIs, handling authentication, and customizing the generated output.

## Overview

MCP Tool Factory can convert any OpenAPI 3.0+ specification into a fully functional MCP server with:

- **Automatic endpoint conversion** - Each operation becomes a tool
- **Authentication handling** - API Key, Bearer, OAuth2, Basic
- **Request/response mapping** - Path, query, body parameters
- **Error handling** - Standard HTTP error responses
- **Type validation** - Based on JSON Schema

## Quick Start

```bash
# Basic import
mcp-factory from-openapi ./petstore.yaml

# With custom base URL
mcp-factory from-openapi ./api.json --base-url https://api.example.com

# With custom name
mcp-factory from-openapi ./spec.yaml --name MyAPIServer
```

## Supported OpenAPI Versions

| Version | Support |
|---------|---------|
| OpenAPI 3.0.x | Full |
| OpenAPI 3.1.x | Full |
| Swagger 2.0 | Not supported |

## File Formats

Both JSON and YAML are supported:

```bash
# JSON
mcp-factory from-openapi ./api.json

# YAML
mcp-factory from-openapi ./api.yaml
mcp-factory from-openapi ./api.yml
```

---

## Authentication

MCP Tool Factory automatically detects and handles authentication from the OpenAPI spec.

### API Key Authentication

**OpenAPI Spec:**

```yaml
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

security:
  - ApiKeyAuth: []
```

**Generated Code:**

```python
# Auth configuration
AUTH_CONFIG = {
    "X_API_KEY": os.environ.get("X_API_KEY"),
}

def require_auth(key_name: str) -> str:
    """Get required auth credential."""
    value = AUTH_CONFIG.get(key_name)
    if not value:
        raise ValueError(f"Missing required auth: {key_name}")
    return value

@mcp.tool()
def get_users() -> dict:
    """Get all users."""
    api_key = require_auth("X_API_KEY")
    response = httpx.get(
        f"{BASE_URL}/users",
        headers={"X-API-Key": api_key}
    )
    return response.json()
```

### Bearer Token Authentication

**OpenAPI Spec:**

```yaml
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - BearerAuth: []
```

**Generated Code:**

```python
@mcp.tool()
def get_data() -> dict:
    token = require_auth("BEARER_TOKEN")
    response = httpx.get(
        f"{BASE_URL}/data",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()
```

### OAuth2 Authentication

**OpenAPI Spec:**

```yaml
components:
  securitySchemes:
    OAuth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://example.com/oauth/authorize
          tokenUrl: https://example.com/oauth/token
          scopes:
            read: Read access
            write: Write access
```

**Generated Code:**

```python
# OAuth2 configuration
OAUTH2_CONFIG = {
    "authorization_url": "https://example.com/oauth/authorize",
    "token_url": "https://example.com/oauth/token",
    "scopes": ["read", "write"],
}

@mcp.tool()
def get_protected_data() -> dict:
    token = require_auth("OAUTH2_ACCESS_TOKEN")
    response = httpx.get(
        f"{BASE_URL}/protected",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()
```

### Basic Authentication

**OpenAPI Spec:**

```yaml
components:
  securitySchemes:
    BasicAuth:
      type: http
      scheme: basic
```

**Generated Code:**

```python
import base64

@mcp.tool()
def get_secure_data() -> dict:
    username = require_auth("BASIC_USERNAME")
    password = require_auth("BASIC_PASSWORD")
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    response = httpx.get(
        f"{BASE_URL}/secure",
        headers={"Authorization": f"Basic {credentials}"}
    )
    return response.json()
```

### API Key Locations

| Location | OpenAPI | Header Name |
|----------|---------|-------------|
| Header | `in: header` | As specified |
| Query | `in: query` | Query parameter |
| Cookie | `in: cookie` | Cookie name |

---

## Parameter Handling

### Path Parameters

**OpenAPI:**

```yaml
paths:
  /users/{userId}:
    get:
      operationId: getUser
      parameters:
        - name: userId
          in: path
          required: true
          schema:
            type: integer
```

**Generated:**

```python
@mcp.tool()
def get_user(user_id: int) -> dict:
    """Get a user by ID."""
    response = httpx.get(f"{BASE_URL}/users/{user_id}")
    return response.json()
```

### Query Parameters

**OpenAPI:**

```yaml
paths:
  /users:
    get:
      operationId: listUsers
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            default: 10
        - name: offset
          in: query
          schema:
            type: integer
            default: 0
```

**Generated:**

```python
@mcp.tool()
def list_users(limit: int = 10, offset: int = 0) -> dict:
    """List users with pagination."""
    response = httpx.get(
        f"{BASE_URL}/users",
        params={"limit": limit, "offset": offset}
    )
    return response.json()
```

### Request Body

**OpenAPI:**

```yaml
paths:
  /users:
    post:
      operationId: createUser
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - name
                - email
              properties:
                name:
                  type: string
                email:
                  type: string
                  format: email
```

**Generated:**

```python
@mcp.tool()
def create_user(name: str, email: str) -> dict:
    """Create a new user.

    Args:
        name: User's name
        email: User's email address
    """
    response = httpx.post(
        f"{BASE_URL}/users",
        json={"name": name, "email": email}
    )
    return response.json()
```

---

## Base URL Detection

MCP Tool Factory automatically detects the base URL from the spec:

**OpenAPI:**

```yaml
servers:
  - url: https://api.example.com/v2
    description: Production
  - url: https://sandbox.example.com/v2
    description: Sandbox
```

**Behavior:**

1. Uses the first server URL by default
2. Can be overridden with `--base-url`

```bash
# Use sandbox instead
mcp-factory from-openapi ./api.yaml --base-url https://sandbox.example.com/v2
```

---

## Operation Naming

Tools are named based on `operationId`:

**OpenAPI:**

```yaml
paths:
  /users:
    get:
      operationId: listUsers
    post:
      operationId: createUser
```

**Generated:**

```python
@mcp.tool()
def list_users() -> dict: ...

@mcp.tool()
def create_user(...) -> dict: ...
```

### Automatic Naming

If `operationId` is not provided, names are generated from method and path:

| Method | Path | Generated Name |
|--------|------|----------------|
| GET | /users | `get_users` |
| POST | /users | `post_users` |
| GET | /users/{id} | `get_users_by_id` |
| PUT | /users/{id} | `put_users_by_id` |
| DELETE | /users/{id} | `delete_users_by_id` |

---

## Error Handling

Generated tools include comprehensive error handling:

```python
@mcp.tool()
def get_user(user_id: int) -> dict:
    """Get a user by ID."""
    try:
        response = httpx.get(f"{BASE_URL}/users/{user_id}")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        return {
            "error": True,
            "status_code": e.response.status_code,
            "message": str(e),
        }
    except httpx.RequestError as e:
        return {
            "error": True,
            "message": f"Request failed: {str(e)}",
        }
```

---

## Programmatic Usage

### Basic Import

```python
import asyncio
import yaml
from tool_factory import ToolFactoryAgent

async def main():
    agent = ToolFactoryAgent()

    with open("api.yaml") as f:
        spec = yaml.safe_load(f)

    result = await agent.generate_from_openapi(
        openapi_spec=spec,
        server_name="MyAPIServer",
    )

    result.write_to_directory("./servers/myapi")

asyncio.run(main())
```

### With Custom Base URL

```python
result = await agent.generate_from_openapi(
    openapi_spec=spec,
    base_url="https://api.example.com/v2",
    server_name="MyAPIServer",
)
```

### Using OpenAPIParser

For more control, use the parser directly:

```python
from tool_factory.openapi import OpenAPIParser, OpenAPIValidator

# Validate first
validator = OpenAPIValidator()
if not validator.validate(spec):
    print(f"Errors: {validator.get_errors()}")
    exit(1)

# Parse
parser = OpenAPIParser(spec)

# Get info
info = parser.get_info()
print(f"API: {info['title']} v{info['version']}")

# Get auth config
auth = parser.get_auth_config()
print(f"Auth: {auth.auth_type.value}")
print(f"Env var: {auth.env_var_name}")

# Get endpoints
endpoints = parser.get_endpoints()
for ep in endpoints:
    print(f"{ep.method.upper()} {ep.path} -> {ep.operation_id}")
```

---

## Advanced Configuration

### Custom Authentication Environment Variables

Override the default environment variable names:

```python
from tool_factory.openapi import OpenAPIParser, AuthConfig, AuthType

parser = OpenAPIParser(spec)

# Override auth config
custom_auth = AuthConfig(
    auth_type=AuthType.API_KEY,
    env_var_name="MY_CUSTOM_API_KEY",
    header_name="X-Custom-Key",
)
```

### Filtering Endpoints

Generate tools for specific paths only:

```python
from tool_factory.openapi import OpenAPIParser

parser = OpenAPIParser(spec)
endpoints = parser.get_endpoints()

# Filter to only /users endpoints
user_endpoints = [ep for ep in endpoints if ep.path.startswith("/users")]
```

---

## Validation

### Validate Before Import

```python
from tool_factory.openapi import OpenAPIValidator

validator = OpenAPIValidator()

with open("api.yaml") as f:
    spec = yaml.safe_load(f)

if validator.validate(spec):
    print("Spec is valid!")
else:
    for error in validator.get_errors():
        print(f"Error: {error}")
```

### Common Validation Errors

| Error | Solution |
|-------|----------|
| Missing `openapi` field | Add `openapi: "3.0.0"` |
| Missing `info` field | Add `info: { title: "", version: "" }` |
| Missing `paths` field | Add at least one path |
| Invalid `$ref` | Check reference paths |
| Invalid schema | Validate against JSON Schema |

---

## Example: Petstore API

Complete example importing the Petstore API:

```yaml
# petstore.yaml
openapi: "3.0.0"
info:
  title: Petstore API
  version: "1.0.0"

servers:
  - url: https://petstore.example.com/v1

components:
  securitySchemes:
    ApiKey:
      type: apiKey
      in: header
      name: X-API-Key

security:
  - ApiKey: []

paths:
  /pets:
    get:
      operationId: listPets
      summary: List all pets
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            default: 10
      responses:
        '200':
          description: List of pets
    post:
      operationId: createPet
      summary: Create a pet
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [name]
              properties:
                name:
                  type: string
                tag:
                  type: string
      responses:
        '201':
          description: Pet created

  /pets/{petId}:
    get:
      operationId: getPet
      summary: Get a pet by ID
      parameters:
        - name: petId
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: Pet details
```

```bash
mcp-factory from-openapi petstore.yaml --name PetstoreServer
```

**Generated `server.py`:**

```python
from mcp.server.fastmcp import FastMCP
import httpx
import os

mcp = FastMCP("PetstoreServer")

BASE_URL = "https://petstore.example.com/v1"

AUTH_CONFIG = {
    "X_API_KEY": os.environ.get("X_API_KEY"),
}

def require_auth(key_name: str) -> str:
    value = AUTH_CONFIG.get(key_name)
    if not value:
        raise ValueError(f"Missing required auth: {key_name}")
    return value

@mcp.tool()
def list_pets(limit: int = 10) -> dict:
    """List all pets."""
    api_key = require_auth("X_API_KEY")
    response = httpx.get(
        f"{BASE_URL}/pets",
        headers={"X-API-Key": api_key},
        params={"limit": limit}
    )
    return response.json()

@mcp.tool()
def create_pet(name: str, tag: str = None) -> dict:
    """Create a pet."""
    api_key = require_auth("X_API_KEY")
    body = {"name": name}
    if tag:
        body["tag"] = tag
    response = httpx.post(
        f"{BASE_URL}/pets",
        headers={"X-API-Key": api_key},
        json=body
    )
    return response.json()

@mcp.tool()
def get_pet(pet_id: int) -> dict:
    """Get a pet by ID."""
    api_key = require_auth("X_API_KEY")
    response = httpx.get(
        f"{BASE_URL}/pets/{pet_id}",
        headers={"X-API-Key": api_key}
    )
    return response.json()

if __name__ == "__main__":
    mcp.run()
```

---

## Troubleshooting

### "OpenAPI spec validation failed"

**Cause:** Invalid or incomplete spec

**Solution:**
1. Validate with `openapi-spec-validator`
2. Check for required fields (`openapi`, `info`, `paths`)
3. Use OpenAPI 3.0+ format

### "Base URL not found"

**Cause:** No `servers` section in spec

**Solution:** Add servers or use `--base-url`:

```bash
mcp-factory from-openapi ./api.yaml --base-url https://api.example.com
```

### "Authentication not detected"

**Cause:** Missing `securitySchemes` or `security`

**Solution:** Add security configuration to your spec or inject auth manually:

```bash
# Generated server will use these env vars
export MY_API_KEY=xxxxx
```
