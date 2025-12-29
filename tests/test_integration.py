"""Integration tests for MCP Tool Factory.

These tests verify complete workflows from input to generated server.
"""

import os
import sqlite3
import tempfile
import subprocess
import sys
from pathlib import Path

import pytest

from tool_factory.database import DatabaseType, DatabaseIntrospector, DatabaseServerGenerator
from tool_factory.openapi import OpenAPIParser, OpenAPIServerGenerator
from tool_factory.generators.server import ServerGenerator
from tool_factory.production import ProductionConfig
from tool_factory.models import ToolSpec


class TestDatabaseIntegrationWorkflow:
    """Test complete database to server workflow."""

    @pytest.fixture
    def sample_database(self):
        """Create a sample SQLite database."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        # Create a realistic schema
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                published BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                body TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Insert sample data
        cursor.execute(
            "INSERT INTO users (username, email) VALUES (?, ?)",
            ("alice", "alice@example.com"),
        )
        cursor.execute(
            "INSERT INTO users (username, email) VALUES (?, ?)",
            ("bob", "bob@example.com"),
        )
        cursor.execute(
            "INSERT INTO posts (user_id, title, content, published) VALUES (?, ?, ?, ?)",
            (1, "Hello World", "My first post!", 1),
        )

        conn.commit()
        conn.close()

        yield path

        os.unlink(path)

    def test_introspection_workflow(self, sample_database):
        """Test database introspection extracts correct schema."""
        introspector = DatabaseIntrospector(DatabaseType.SQLITE, sample_database)
        tables = introspector.get_tables()

        assert len(tables) == 3
        table_names = {t.name for t in tables}
        assert table_names == {"users", "posts", "comments"}

        # Check users table structure
        users = next(t for t in tables if t.name == "users")
        assert len(users.columns) == 4
        assert users.primary_key.name == "id"

        # Check foreign keys detected
        posts = next(t for t in tables if t.name == "posts")
        user_id_col = next(c for c in posts.columns if c.name == "user_id")
        assert user_id_col.foreign_key == "users.id"

    def test_server_generation_workflow(self, sample_database):
        """Test full server generation from database."""
        gen = DatabaseServerGenerator(DatabaseType.SQLITE, sample_database)
        code = gen.generate_server_code("BlogServer")

        # Verify code compiles
        compile(code, "<string>", "exec")

        # Check all expected tools are generated
        expected_tools = [
            "get_users", "list_users", "create_users", "update_users", "delete_users",
            "get_posts", "list_posts", "create_posts", "update_posts", "delete_posts",
            "get_comments", "list_comments", "create_comments", "update_comments", "delete_comments",
        ]
        for tool in expected_tools:
            assert tool in code, f"Missing tool: {tool}"

        # Check health check exists
        assert "def health_check()" in code

        # Check proper database connection setup
        assert "get_connection()" in code
        assert "sqlite3.connect" in code

    def test_tool_specs_generation(self, sample_database):
        """Test tool specification generation."""
        gen = DatabaseServerGenerator(DatabaseType.SQLITE, sample_database)
        specs = gen.get_tool_specs()

        # 5 tools per table with PK × 3 tables = 15 tools
        assert len(specs) == 15

        # Check specific tool specs
        get_users = next(s for s in specs if s.name == "get_users")
        assert "id" in get_users.input_schema["properties"]
        assert "id" in get_users.input_schema["required"]

        list_users = next(s for s in specs if s.name == "list_users")
        assert "username" in list_users.input_schema["properties"]
        assert "limit" in list_users.input_schema["properties"]


class TestOpenAPIIntegrationWorkflow:
    """Test complete OpenAPI to server workflow."""

    @pytest.fixture
    def petstore_spec(self):
        """A realistic PetStore-like OpenAPI spec."""
        return {
            "openapi": "3.0.3",
            "info": {
                "title": "Pet Store API",
                "description": "A sample Pet Store API",
                "version": "1.0.0",
            },
            "servers": [
                {"url": "https://api.petstore.example.com/v1"}
            ],
            "components": {
                "securitySchemes": {
                    "apiKey": {
                        "type": "apiKey",
                        "name": "X-API-Key",
                        "in": "header",
                    }
                }
            },
            "security": [{"apiKey": []}],
            "paths": {
                "/pets": {
                    "get": {
                        "operationId": "listPets",
                        "summary": "List all pets",
                        "description": "Returns a list of all pets in the store",
                        "tags": ["pets"],
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "description": "Maximum number of pets to return",
                                "schema": {"type": "integer", "default": 20},
                            },
                            {
                                "name": "species",
                                "in": "query",
                                "description": "Filter by species",
                                "schema": {"type": "string"},
                            },
                        ],
                        "responses": {
                            "200": {"description": "A list of pets"},
                        },
                    },
                    "post": {
                        "operationId": "createPet",
                        "summary": "Create a new pet",
                        "tags": ["pets"],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["name", "species"],
                                        "properties": {
                                            "name": {"type": "string"},
                                            "species": {"type": "string"},
                                            "age": {"type": "integer"},
                                        },
                                    }
                                }
                            },
                        },
                        "responses": {
                            "201": {"description": "Pet created"},
                        },
                    },
                },
                "/pets/{petId}": {
                    "get": {
                        "operationId": "getPet",
                        "summary": "Get a pet by ID",
                        "tags": ["pets"],
                        "parameters": [
                            {
                                "name": "petId",
                                "in": "path",
                                "required": True,
                                "description": "The pet ID",
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {
                            "200": {"description": "The pet details"},
                            "404": {"description": "Pet not found"},
                        },
                    },
                    "delete": {
                        "operationId": "deletePet",
                        "summary": "Delete a pet",
                        "tags": ["pets"],
                        "parameters": [
                            {
                                "name": "petId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {
                            "204": {"description": "Pet deleted"},
                        },
                    },
                },
                "/stores": {
                    "get": {
                        "operationId": "listStores",
                        "summary": "List all stores",
                        "tags": ["stores"],
                        "responses": {
                            "200": {"description": "A list of stores"},
                        },
                    },
                },
            },
        }

    def test_parser_workflow(self, petstore_spec):
        """Test OpenAPI parsing extracts correct information."""
        parser = OpenAPIParser(petstore_spec)

        # Check info
        info = parser.get_info()
        assert info["title"] == "Pet Store API"
        assert info["version"] == "1.0.0"

        # Check servers
        servers = parser.get_servers()
        assert len(servers) == 1
        assert servers[0]["url"] == "https://api.petstore.example.com/v1"

        # Check auth
        auth = parser.get_auth_config()
        assert auth.auth_type.value == "apiKey"
        assert auth.header_name == "X-API-Key"

        # Check endpoints
        endpoints = parser.get_endpoints()
        assert len(endpoints) == 5

        op_ids = {e.operation_id for e in endpoints}
        assert op_ids == {"listPets", "createPet", "getPet", "deletePet", "listStores"}

    def test_server_generation_workflow(self, petstore_spec):
        """Test full server generation from OpenAPI."""
        gen = OpenAPIServerGenerator(petstore_spec)
        code = gen.generate_server_code("PetStoreServer")

        # Verify code compiles
        compile(code, "<string>", "exec")

        # Check all expected tools
        assert "listpets" in code.lower()
        assert "createpet" in code.lower()
        assert "getpet" in code.lower()
        assert "deletepet" in code.lower()
        assert "liststores" in code.lower()

        # Check auth is configured
        assert "X-API-Key" in code
        assert "API_KEY" in code

        # Check HTTP client setup
        assert "_make_request" in code
        assert "httpx" in code

        # Check base URL
        assert "https://api.petstore.example.com/v1" in code

    def test_tool_specs_generation(self, petstore_spec):
        """Test tool specification generation from OpenAPI."""
        gen = OpenAPIServerGenerator(petstore_spec)
        specs = gen.get_tool_specs()

        assert len(specs) == 5

        # Check listPets spec
        list_pets = next(s for s in specs if s.name == "listpets")
        assert "limit" in list_pets.input_schema["properties"]
        assert "species" in list_pets.input_schema["properties"]

        # Check getPet spec
        get_pet = next(s for s in specs if s.name == "getpet")
        assert "petId" in get_pet.input_schema["properties"]
        assert "petId" in get_pet.input_schema["required"]

    def test_auth_env_vars(self, petstore_spec):
        """Test auth environment variable detection."""
        gen = OpenAPIServerGenerator(petstore_spec)
        env_vars = gen.get_auth_env_vars()

        assert len(env_vars) == 1
        assert "API_KEY" in env_vars[0]


class TestProductionFeaturesIntegration:
    """Test production features integration with generators."""

    @pytest.fixture
    def sample_spec(self):
        """Create a sample tool specification."""
        return ToolSpec(
            name="calculate",
            description="Perform a calculation",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        )

    def test_production_config_integration(self, sample_spec):
        """Test production config is integrated into generated code."""
        config = ProductionConfig(
            enable_logging=True,
            enable_metrics=True,
            enable_rate_limiting=True,
            rate_limit_requests=50,
        )

        generator = ServerGenerator()
        code = generator.generate_server_simple(
            server_name="CalcServer",
            tool_specs=[sample_spec],
            implementations={
                "calculate": '''def calculate(a: float, b: float) -> dict:
    """Calculate sum."""
    return {"result": a + b}'''
            },
            production_config=config,
        )

        # Check production features are included
        assert "STRUCTURED LOGGING" in code
        assert "PROMETHEUS METRICS" in code
        assert "RATE LIMITING" in code

        # Check rate limit config
        assert "50" in code  # rate_limit_requests

        # Verify code compiles
        compile(code, "<string>", "exec")

    def test_all_production_features(self, sample_spec):
        """Test all production features together."""
        config = ProductionConfig(
            enable_logging=True,
            log_json=True,
            enable_metrics=True,
            metrics_port=9090,
            enable_rate_limiting=True,
            rate_limit_requests=100,
            rate_limit_window_seconds=60,
            enable_retries=True,
            max_retries=3,
        )

        generator = ServerGenerator()
        code = generator.generate_server_simple(
            server_name="FullServer",
            tool_specs=[sample_spec],
            implementations={
                "calculate": '''def calculate(a: float, b: float) -> dict:
    return {"result": a + b}'''
            },
            production_config=config,
        )

        # All features present
        assert "JSONFormatter" in code
        assert "prometheus_client" in code or "PROMETHEUS METRICS" in code
        assert "RateLimiter" in code
        assert "retry_with_backoff" in code

        # Verify compiles
        compile(code, "<string>", "exec")


class TestCLIIntegration:
    """Test CLI commands work correctly."""

    def test_cli_help(self):
        """Test CLI help command works."""
        result = subprocess.run(
            [sys.executable, "-m", "tool_factory.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "generate" in result.stdout or "MCP" in result.stdout

    def test_cli_from_database_help(self):
        """Test from-database subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "tool_factory.cli", "from-database", "--help"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "database" in result.stdout.lower() or "sqlite" in result.stdout.lower()

    def test_cli_from_openapi_help(self):
        """Test from-openapi subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "tool_factory.cli", "from-openapi", "--help"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "openapi" in result.stdout.lower() or "spec" in result.stdout.lower()


class TestEndToEndWorkflow:
    """End-to-end tests that generate and validate complete servers."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp(prefix="mcp_factory_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_database_server_is_syntactically_valid(self, temp_output_dir):
        """Test generated database server is valid Python."""
        # Create test database
        db_path = os.path.join(temp_output_dir, "test.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                quantity INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

        # Generate server
        gen = DatabaseServerGenerator(DatabaseType.SQLITE, db_path)
        code = gen.generate_server_code("ItemsServer")

        # Write to file
        server_path = os.path.join(temp_output_dir, "server.py")
        with open(server_path, "w") as f:
            f.write(code)

        # Verify syntax by compiling
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", server_path],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_openapi_server_is_syntactically_valid(self, temp_output_dir):
        """Test generated OpenAPI server is valid Python."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "https://api.test.com"}],
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "listItems",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        gen = OpenAPIServerGenerator(spec)
        code = gen.generate_server_code("TestServer")

        # Write to file
        server_path = os.path.join(temp_output_dir, "server.py")
        with open(server_path, "w") as f:
            f.write(code)

        # Verify syntax
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", server_path],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"
