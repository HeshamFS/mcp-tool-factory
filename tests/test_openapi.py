"""Tests for OpenAPI parser and generator module."""

import pytest
from tool_factory.openapi import (
    AuthType,
    AuthConfig,
    EndpointSpec,
    OpenAPIParser,
    OpenAPIServerGenerator,
    OpenAPIValidator,
    OpenAPIValidationError,
)


class TestAuthType:
    """Tests for AuthType enum."""

    def test_auth_type_values(self):
        """Test all auth types are defined."""
        assert AuthType.NONE.value == "none"
        assert AuthType.API_KEY.value == "apiKey"
        assert AuthType.BEARER.value == "bearer"
        assert AuthType.OAUTH2.value == "oauth2"
        assert AuthType.BASIC.value == "basic"


class TestAuthConfig:
    """Tests for AuthConfig dataclass."""

    def test_default_values(self):
        """Test default auth config."""
        config = AuthConfig()
        assert config.auth_type == AuthType.NONE
        assert config.env_var_name == ""
        assert config.header_name == ""
        assert config.in_location == ""
        assert config.scheme == ""

    def test_to_env_check_code_none(self):
        """Test no env check code when auth is NONE."""
        config = AuthConfig(auth_type=AuthType.NONE)
        assert config.to_env_check_code() == ""

    def test_to_env_check_code_api_key(self):
        """Test env check code for API key auth."""
        config = AuthConfig(
            auth_type=AuthType.API_KEY,
            env_var_name="MY_API_KEY",
        )
        code = config.to_env_check_code()

        assert "MY_API_KEY" in code
        assert 'os.environ.get("MY_API_KEY")' in code
        assert "ValueError" in code

    def test_to_header_code_none(self):
        """Test header code when auth is NONE."""
        config = AuthConfig(auth_type=AuthType.NONE)
        code = config.to_header_code()
        assert code == "headers = {}"

    def test_to_header_code_bearer(self):
        """Test header code for bearer auth."""
        config = AuthConfig(
            auth_type=AuthType.BEARER,
            env_var_name="ACCESS_TOKEN",
        )
        code = config.to_header_code()

        assert "Authorization" in code
        assert "Bearer" in code
        assert "ACCESS_TOKEN" in code

    def test_to_header_code_api_key_header(self):
        """Test header code for API key in header."""
        config = AuthConfig(
            auth_type=AuthType.API_KEY,
            env_var_name="MY_API_KEY",
            header_name="X-API-Key",
            in_location="header",
        )
        code = config.to_header_code()

        assert "X-API-Key" in code
        assert "MY_API_KEY" in code

    def test_to_header_code_api_key_query(self):
        """Test header code for API key in query (no headers needed)."""
        config = AuthConfig(
            auth_type=AuthType.API_KEY,
            env_var_name="MY_API_KEY",
            in_location="query",
        )
        code = config.to_header_code()
        assert code == "headers = {}"

    def test_to_header_code_basic(self):
        """Test header code for basic auth."""
        config = AuthConfig(
            auth_type=AuthType.BASIC,
            env_var_name="CREDENTIALS",
        )
        code = config.to_header_code()

        assert "base64" in code
        assert "Authorization" in code
        assert "Basic" in code


class TestEndpointSpec:
    """Tests for EndpointSpec dataclass."""

    def test_default_values(self):
        """Test default endpoint spec."""
        spec = EndpointSpec(
            path="/test",
            method="GET",
            operation_id="test_op",
            summary="Test",
            description="Test endpoint",
        )
        assert spec.path == "/test"
        assert spec.method == "GET"
        assert spec.parameters == []
        assert spec.request_body is None
        assert spec.responses == {}
        assert spec.security == []
        assert spec.tags == []


class TestOpenAPIParser:
    """Tests for OpenAPIParser."""

    @pytest.fixture
    def simple_spec(self):
        """A simple OpenAPI 3.0 spec."""
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "version": "1.0.0",
                "description": "A test API",
            },
            "servers": [
                {"url": "https://api.example.com/v1"}
            ],
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "summary": "List all users",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer"},
                                "required": False,
                            }
                        ],
                        "responses": {"200": {"description": "Success"}},
                    },
                    "post": {
                        "operationId": "createUser",
                        "summary": "Create a user",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    },
                },
                "/users/{id}": {
                    "get": {
                        "operationId": "getUser",
                        "summary": "Get a user",
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "schema": {"type": "integer"},
                                "required": True,
                            }
                        ],
                        "responses": {"200": {"description": "Success"}},
                    },
                },
            },
        }

    @pytest.fixture
    def api_key_spec(self):
        """OpenAPI spec with API key auth."""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Secured API", "version": "1.0.0"},
            "servers": [{"url": "https://api.secure.com"}],
            "components": {
                "securitySchemes": {
                    "apiKey": {
                        "type": "apiKey",
                        "name": "X-API-Key",
                        "in": "header",
                    }
                }
            },
            "paths": {},
        }

    @pytest.fixture
    def bearer_spec(self):
        """OpenAPI spec with bearer token auth."""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Bearer API", "version": "1.0.0"},
            "servers": [{"url": "https://api.bearer.com"}],
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                    }
                }
            },
            "paths": {},
        }

    @pytest.fixture
    def swagger_spec(self):
        """Swagger 2.0 spec."""
        return {
            "swagger": "2.0",
            "info": {"title": "Swagger API", "version": "1.0.0"},
            "host": "api.swagger.com",
            "basePath": "/v2",
            "schemes": ["https"],
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "getItems",
                        "summary": "Get items",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

    def test_detect_version_openapi3(self, simple_spec):
        """Test OpenAPI 3.x version detection."""
        parser = OpenAPIParser(simple_spec)
        assert parser.version == "3.0.0"

    def test_detect_version_swagger2(self, swagger_spec):
        """Test Swagger 2.0 version detection."""
        parser = OpenAPIParser(swagger_spec)
        assert parser.version == "2.0"

    def test_get_info(self, simple_spec):
        """Test extracting API info."""
        parser = OpenAPIParser(simple_spec)
        info = parser.get_info()

        assert info["title"] == "Test API"
        assert info["version"] == "1.0.0"
        assert info["description"] == "A test API"

    def test_get_servers_openapi3(self, simple_spec):
        """Test extracting servers from OpenAPI 3.x."""
        parser = OpenAPIParser(simple_spec)
        servers = parser.get_servers()

        assert len(servers) == 1
        assert servers[0]["url"] == "https://api.example.com/v1"

    def test_get_servers_swagger2(self, swagger_spec):
        """Test constructing server URL from Swagger 2.0."""
        parser = OpenAPIParser(swagger_spec)
        servers = parser.get_servers()

        assert len(servers) == 1
        assert servers[0]["url"] == "https://api.swagger.com/v2"

    def test_get_auth_config_none(self, simple_spec):
        """Test no auth when none defined."""
        parser = OpenAPIParser(simple_spec)
        auth = parser.get_auth_config()

        assert auth.auth_type == AuthType.NONE

    def test_get_auth_config_api_key(self, api_key_spec):
        """Test API key auth extraction."""
        parser = OpenAPIParser(api_key_spec)
        auth = parser.get_auth_config()

        assert auth.auth_type == AuthType.API_KEY
        assert "API_KEY" in auth.env_var_name
        assert auth.header_name == "X-API-Key"
        assert auth.in_location == "header"

    def test_get_auth_config_bearer(self, bearer_spec):
        """Test bearer token auth extraction."""
        parser = OpenAPIParser(bearer_spec)
        auth = parser.get_auth_config()

        assert auth.auth_type == AuthType.BEARER
        assert "TOKEN" in auth.env_var_name
        assert auth.scheme == "bearer"

    def test_get_endpoints(self, simple_spec):
        """Test extracting all endpoints."""
        parser = OpenAPIParser(simple_spec)
        endpoints = parser.get_endpoints()

        # Should have 3 endpoints: GET /users, POST /users, GET /users/{id}
        assert len(endpoints) == 3

        # Check GET /users
        get_users = next(e for e in endpoints if e.operation_id == "listUsers")
        assert get_users.path == "/users"
        assert get_users.method == "GET"
        assert get_users.summary == "List all users"
        assert len(get_users.parameters) == 1
        assert get_users.parameters[0]["name"] == "limit"

        # Check POST /users
        create_user = next(e for e in endpoints if e.operation_id == "createUser")
        assert create_user.method == "POST"
        assert create_user.request_body is not None

        # Check GET /users/{id}
        get_user = next(e for e in endpoints if e.operation_id == "getUser")
        assert get_user.path == "/users/{id}"
        assert len(get_user.parameters) == 1
        assert get_user.parameters[0]["name"] == "id"
        assert get_user.parameters[0]["required"] is True

    def test_resolve_ref(self, simple_spec):
        """Test reference resolution."""
        # Add a $ref to the spec
        simple_spec["components"] = {
            "parameters": {
                "PageLimit": {
                    "name": "limit",
                    "in": "query",
                    "schema": {"type": "integer", "maximum": 100},
                }
            }
        }
        simple_spec["paths"]["/users"]["get"]["parameters"] = [
            {"$ref": "#/components/parameters/PageLimit"}
        ]

        parser = OpenAPIParser(simple_spec)
        endpoints = parser.get_endpoints()

        get_users = next(e for e in endpoints if e.operation_id == "listUsers")
        # Parameter should be resolved
        assert get_users.parameters[0]["name"] == "limit"

    def test_generated_operation_id(self):
        """Test auto-generated operation IDs."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/items": {
                    "get": {
                        # No operationId
                        "summary": "Get items",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        parser = OpenAPIParser(spec)
        endpoints = parser.get_endpoints()

        assert len(endpoints) == 1
        assert endpoints[0].operation_id == "get_items"


class TestOpenAPIServerGenerator:
    """Tests for OpenAPIServerGenerator."""

    @pytest.fixture
    def simple_spec(self):
        """A simple OpenAPI spec."""
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "Pet Store",
                "version": "1.0.0",
            },
            "servers": [{"url": "https://petstore.example.com/api"}],
            "paths": {
                "/pets": {
                    "get": {
                        "operationId": "listPets",
                        "summary": "List all pets",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer"},
                                "required": False,
                            }
                        ],
                        "responses": {"200": {"description": "Success"}},
                    },
                },
            },
        }

    @pytest.fixture
    def secured_spec(self):
        """OpenAPI spec with security."""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Secured API", "version": "1.0.0"},
            "servers": [{"url": "https://api.secure.com"}],
            "components": {
                "securitySchemes": {
                    "apiKey": {
                        "type": "apiKey",
                        "name": "X-API-Key",
                        "in": "header",
                    }
                }
            },
            "paths": {
                "/data": {
                    "get": {
                        "operationId": "getData",
                        "summary": "Get secured data",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

    def test_base_url_from_spec(self, simple_spec):
        """Test base URL extraction from spec."""
        gen = OpenAPIServerGenerator(simple_spec)
        assert gen.base_url == "https://petstore.example.com/api"

    def test_base_url_override(self, simple_spec):
        """Test overriding base URL."""
        gen = OpenAPIServerGenerator(simple_spec, base_url="https://custom.url/v2/")
        assert gen.base_url == "https://custom.url/v2"

    def test_generate_server_code_structure(self, simple_spec):
        """Test generated server code structure."""
        gen = OpenAPIServerGenerator(simple_spec)
        code = gen.generate_server_code("PetStoreServer")

        # Check imports
        assert "import os" in code
        assert "import httpx" in code
        assert "from mcp.server.fastmcp import FastMCP" in code

        # Check server setup
        assert 'FastMCP("PetStoreServer"' in code
        assert "BASE_URL" in code

        # Check health check
        assert "def health_check()" in code
        assert "Pet Store" in code

        # Check tool
        assert "listpets" in code.lower()

        # Check main block
        assert 'if __name__ == "__main__"' in code
        assert "mcp.run" in code

    def test_generate_server_code_with_auth(self, secured_spec):
        """Test server code with authentication."""
        gen = OpenAPIServerGenerator(secured_spec)
        code = gen.generate_server_code("SecuredServer")

        # Check auth configuration
        assert "API_KEY" in code
        assert "os.environ.get" in code
        assert "X-API-Key" in code

    def test_get_tool_specs(self, simple_spec):
        """Test tool spec extraction."""
        gen = OpenAPIServerGenerator(simple_spec)
        specs = gen.get_tool_specs()

        assert len(specs) == 1
        spec = specs[0]
        assert spec.name == "listpets"
        assert "pets" in spec.description.lower() or "list" in spec.description.lower()
        assert "httpx" in spec.dependencies

    def test_get_auth_env_vars_no_auth(self, simple_spec):
        """Test no auth env vars when no auth configured."""
        gen = OpenAPIServerGenerator(simple_spec)
        env_vars = gen.get_auth_env_vars()
        assert env_vars == []

    def test_get_auth_env_vars_with_auth(self, secured_spec):
        """Test auth env vars extraction."""
        gen = OpenAPIServerGenerator(secured_spec)
        env_vars = gen.get_auth_env_vars()

        assert len(env_vars) == 1
        assert "API_KEY" in env_vars[0]

    def test_sanitize_operation_id(self, simple_spec):
        """Test operation ID sanitization."""
        gen = OpenAPIServerGenerator(simple_spec)

        # Test various inputs
        assert gen._sanitize_name("get-users") == "get_users"
        assert gen._sanitize_name("Get Users") == "get_users"
        assert gen._sanitize_name("1invalid") == "op_1invalid"
        assert gen._sanitize_name("hello.world") == "hello_world"

    def test_schema_to_python_type(self, simple_spec):
        """Test JSON schema to Python type conversion."""
        gen = OpenAPIServerGenerator(simple_spec)

        assert gen._schema_to_python_type({"type": "string"}) == "str"
        assert gen._schema_to_python_type({"type": "integer"}) == "int"
        assert gen._schema_to_python_type({"type": "number"}) == "float"
        assert gen._schema_to_python_type({"type": "boolean"}) == "bool"
        assert gen._schema_to_python_type({"type": "array"}) == "list"
        assert gen._schema_to_python_type({"type": "object"}) == "dict"
        assert gen._schema_to_python_type({}) == "str"  # Default

    def test_get_default_value(self, simple_spec):
        """Test default value generation."""
        gen = OpenAPIServerGenerator(simple_spec)

        assert gen._get_default_value({"default": "hello"}) == '"hello"'
        assert gen._get_default_value({"default": 42}) == "42"
        assert gen._get_default_value({"default": True}) == "True"
        assert gen._get_default_value({}) == "None"


class TestOpenAPIEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_spec(self):
        """Test handling of empty spec."""
        spec = {}
        parser = OpenAPIParser(spec)

        assert parser.get_info() == {}
        assert parser.get_endpoints() == []
        assert parser.get_auth_config().auth_type == AuthType.NONE

    def test_no_paths(self):
        """Test spec with no paths."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Empty", "version": "1.0.0"},
        }
        parser = OpenAPIParser(spec)
        assert parser.get_endpoints() == []

    def test_path_level_parameters(self):
        """Test path-level parameters are included."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/users/{userId}/posts": {
                    "parameters": [
                        {
                            "name": "userId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "getUserPosts",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    },
                }
            },
        }

        parser = OpenAPIParser(spec)
        endpoints = parser.get_endpoints()

        assert len(endpoints) == 1
        # Should have both path-level and operation-level parameters
        assert len(endpoints[0].parameters) == 2

    def test_multiple_auth_schemes(self):
        """Test only first auth scheme is used."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Multi-Auth", "version": "1.0.0"},
            "components": {
                "securitySchemes": {
                    "apiKey": {
                        "type": "apiKey",
                        "name": "X-API-Key",
                        "in": "header",
                    },
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                    },
                }
            },
            "paths": {},
        }

        parser = OpenAPIParser(spec)
        auth = parser.get_auth_config()

        # Should use first scheme (order may vary in dict)
        assert auth.auth_type in [AuthType.API_KEY, AuthType.BEARER]

    def test_oauth2_auth(self):
        """Test OAuth2 auth detection."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "OAuth2 API", "version": "1.0.0"},
            "components": {
                "securitySchemes": {
                    "oauth2": {
                        "type": "oauth2",
                        "flows": {
                            "authorizationCode": {
                                "authorizationUrl": "https://example.com/oauth/authorize",
                                "tokenUrl": "https://example.com/oauth/token",
                            }
                        },
                    }
                }
            },
            "paths": {},
        }

        parser = OpenAPIParser(spec)
        auth = parser.get_auth_config()

        assert auth.auth_type == AuthType.OAUTH2
        assert "TOKEN" in auth.env_var_name

    def test_request_body_handling(self):
        """Test proper request body parameter generation."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "servers": [{"url": "https://api.test.com"}],
            "paths": {
                "/items": {
                    "post": {
                        "operationId": "createItem",
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
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        gen = OpenAPIServerGenerator(spec)
        code = gen.generate_server_code("TestServer")

        assert "request_body: dict" in code
        assert "json_body = request_body" in code


class TestOpenAPIValidator:
    """Tests for OpenAPI specification validation."""

    def test_valid_spec(self):
        """Test validation of a valid spec."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {"/items": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
        errors = OpenAPIValidator.validate(spec, raise_on_error=False)
        assert len(errors) == 0

    def test_missing_openapi_version(self):
        """Test validation fails for missing version."""
        spec = {
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {},
        }
        errors = OpenAPIValidator.validate(spec, raise_on_error=False)
        assert any("version" in e.lower() for e in errors)

    def test_missing_info_section(self):
        """Test validation fails for missing info."""
        spec = {
            "openapi": "3.0.0",
            "paths": {},
        }
        errors = OpenAPIValidator.validate(spec, raise_on_error=False)
        assert any("info" in e.lower() for e in errors)

    def test_missing_paths_section(self):
        """Test validation fails for missing paths."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
        }
        errors = OpenAPIValidator.validate(spec, raise_on_error=False)
        assert any("paths" in e.lower() for e in errors)

    def test_invalid_path_format(self):
        """Test validation fails for path not starting with /."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {"items": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }
        errors = OpenAPIValidator.validate(spec, raise_on_error=False)
        assert any("start with '/'" in e for e in errors)

    def test_invalid_server_url(self):
        """Test validation fails for invalid server URL."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {"/items": {}},
            "servers": [{"url": "ftp://example.com"}],
        }
        errors = OpenAPIValidator.validate(spec, raise_on_error=False)
        assert any("scheme" in e.lower() for e in errors)

    def test_valid_server_with_template_vars(self):
        """Test validation accepts server URLs with template variables."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {"/items": {}},
            "servers": [{"url": "https://{subdomain}.example.com/api/{version}"}],
        }
        errors = OpenAPIValidator.validate(spec, raise_on_error=False)
        assert not any("server" in e.lower() for e in errors)

    def test_raise_on_error(self):
        """Test that raise_on_error raises exception."""
        spec = {"invalid": "spec"}
        with pytest.raises(OpenAPIValidationError) as exc_info:
            OpenAPIValidator.validate(spec, raise_on_error=True)
        assert len(exc_info.value.errors) > 0

    def test_swagger_2_version(self):
        """Test validation accepts Swagger 2.0 version."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {"/items": {}},
        }
        errors = OpenAPIValidator.validate(spec, raise_on_error=False)
        assert not any("version" in e.lower() for e in errors)

    def test_non_dict_spec(self):
        """Test validation fails for non-dict input."""
        with pytest.raises(OpenAPIValidationError):
            OpenAPIValidator.validate("not a dict", raise_on_error=True)
