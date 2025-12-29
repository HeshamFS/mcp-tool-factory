"""Tests for database introspection and CRUD generator module."""

import os
import sqlite3
import tempfile

import pytest

from tool_factory.database import (
    ColumnInfo,
    DatabaseIntrospector,
    DatabaseServerGenerator,
    DatabaseType,
    TableInfo,
)


class TestDatabaseType:
    """Tests for DatabaseType enum."""

    def test_database_types(self):
        """Test database type values."""
        assert DatabaseType.SQLITE.value == "sqlite"
        assert DatabaseType.POSTGRESQL.value == "postgresql"


class TestColumnInfo:
    """Tests for ColumnInfo dataclass."""

    def test_default_values(self):
        """Test default column info values."""
        col = ColumnInfo(name="id", data_type="INTEGER")
        assert col.name == "id"
        assert col.data_type == "INTEGER"
        assert col.is_nullable is True
        assert col.is_primary_key is False
        assert col.default_value is None
        assert col.foreign_key is None

    def test_to_python_type_integer(self):
        """Test integer type conversion."""
        for sql_type in ["INTEGER", "INT", "BIGINT", "SMALLINT", "SERIAL"]:
            col = ColumnInfo(name="id", data_type=sql_type)
            assert col.to_python_type() == "int"

    def test_to_python_type_float(self):
        """Test float type conversion."""
        for sql_type in ["REAL", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC"]:
            col = ColumnInfo(name="value", data_type=sql_type)
            assert col.to_python_type() == "float"

    def test_to_python_type_bool(self):
        """Test boolean type conversion."""
        for sql_type in ["BOOLEAN", "BOOL"]:
            col = ColumnInfo(name="active", data_type=sql_type)
            assert col.to_python_type() == "bool"

    def test_to_python_type_json(self):
        """Test JSON type conversion."""
        for sql_type in ["JSON", "JSONB"]:
            col = ColumnInfo(name="data", data_type=sql_type)
            assert col.to_python_type() == "dict"

    def test_to_python_type_array(self):
        """Test array type conversion."""
        col = ColumnInfo(name="tags", data_type="TEXT[]")
        assert col.to_python_type() == "list"

    def test_to_python_type_string(self):
        """Test string type conversion (default)."""
        for sql_type in ["TEXT", "VARCHAR", "CHAR", "UUID"]:
            col = ColumnInfo(name="name", data_type=sql_type)
            assert col.to_python_type() == "str"

    def test_to_json_schema_type(self):
        """Test JSON Schema type conversion."""
        test_cases = [
            ("INTEGER", "integer"),
            ("REAL", "number"),
            ("BOOLEAN", "boolean"),
            ("JSON", "object"),
            ("TEXT[]", "array"),
            ("TEXT", "string"),
        ]
        for sql_type, expected in test_cases:
            col = ColumnInfo(name="test", data_type=sql_type)
            assert col.to_json_schema_type() == expected


class TestTableInfo:
    """Tests for TableInfo dataclass."""

    def test_default_values(self):
        """Test default table info values."""
        table = TableInfo(name="users")
        assert table.name == "users"
        assert table.columns == []
        assert table.schema == "public"

    def test_primary_key_found(self):
        """Test primary key detection."""
        table = TableInfo(
            name="users",
            columns=[
                ColumnInfo(name="id", data_type="INTEGER", is_primary_key=True),
                ColumnInfo(name="name", data_type="TEXT"),
            ],
        )
        pk = table.primary_key
        assert pk is not None
        assert pk.name == "id"

    def test_primary_key_not_found(self):
        """Test when no primary key exists."""
        table = TableInfo(
            name="users",
            columns=[
                ColumnInfo(name="name", data_type="TEXT"),
                ColumnInfo(name="email", data_type="TEXT"),
            ],
        )
        assert table.primary_key is None

    def test_non_pk_columns(self):
        """Test non-primary key columns."""
        table = TableInfo(
            name="users",
            columns=[
                ColumnInfo(name="id", data_type="INTEGER", is_primary_key=True),
                ColumnInfo(name="name", data_type="TEXT"),
                ColumnInfo(name="email", data_type="TEXT"),
            ],
        )
        non_pk = table.non_pk_columns
        assert len(non_pk) == 2
        assert all(not col.is_primary_key for col in non_pk)


class TestDatabaseIntrospector:
    """Tests for DatabaseIntrospector with SQLite."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database with test schema."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        # Create test tables
        cursor.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        conn.commit()
        conn.close()

        yield path

        # Cleanup
        os.unlink(path)

    def test_get_tables(self, temp_db):
        """Test table introspection."""
        introspector = DatabaseIntrospector(DatabaseType.SQLITE, temp_db)
        tables = introspector.get_tables()

        assert len(tables) == 2
        table_names = [t.name for t in tables]
        assert "users" in table_names
        assert "posts" in table_names

    def test_get_columns(self, temp_db):
        """Test column introspection."""
        introspector = DatabaseIntrospector(DatabaseType.SQLITE, temp_db)
        tables = introspector.get_tables()

        users = next(t for t in tables if t.name == "users")
        assert len(users.columns) == 4

        col_names = [c.name for c in users.columns]
        assert "id" in col_names
        assert "name" in col_names
        assert "email" in col_names
        assert "created_at" in col_names

    def test_primary_key_detection(self, temp_db):
        """Test primary key detection."""
        introspector = DatabaseIntrospector(DatabaseType.SQLITE, temp_db)
        tables = introspector.get_tables()

        users = next(t for t in tables if t.name == "users")
        pk = users.primary_key

        assert pk is not None
        assert pk.name == "id"
        assert pk.is_primary_key is True

    def test_nullable_detection(self, temp_db):
        """Test nullable column detection."""
        introspector = DatabaseIntrospector(DatabaseType.SQLITE, temp_db)
        tables = introspector.get_tables()

        users = next(t for t in tables if t.name == "users")

        name_col = next(c for c in users.columns if c.name == "name")
        email_col = next(c for c in users.columns if c.name == "email")

        assert name_col.is_nullable is False  # NOT NULL
        assert email_col.is_nullable is True  # nullable

    def test_foreign_key_detection(self, temp_db):
        """Test foreign key detection."""
        introspector = DatabaseIntrospector(DatabaseType.SQLITE, temp_db)
        tables = introspector.get_tables()

        posts = next(t for t in tables if t.name == "posts")
        user_id_col = next(c for c in posts.columns if c.name == "user_id")

        assert user_id_col.foreign_key == "users.id"


class TestDatabaseServerGenerator:
    """Tests for DatabaseServerGenerator."""

    @pytest.fixture
    def sample_tables(self):
        """Create sample table info for testing."""
        return [
            TableInfo(
                name="users",
                columns=[
                    ColumnInfo(name="id", data_type="INTEGER", is_primary_key=True),
                    ColumnInfo(name="name", data_type="TEXT", is_nullable=False),
                    ColumnInfo(name="email", data_type="TEXT"),
                ],
            ),
            TableInfo(
                name="posts",
                columns=[
                    ColumnInfo(name="id", data_type="INTEGER", is_primary_key=True),
                    ColumnInfo(
                        name="user_id", data_type="INTEGER", foreign_key="users.id"
                    ),
                    ColumnInfo(name="title", data_type="TEXT", is_nullable=False),
                    ColumnInfo(name="content", data_type="TEXT"),
                ],
            ),
        ]

    def test_generate_imports_sqlite(self, sample_tables):
        """Test import generation for SQLite."""
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=sample_tables,
        )
        code = gen._generate_imports()

        assert "import sqlite3" in code
        assert "from mcp.server.fastmcp import FastMCP" in code

    def test_generate_imports_postgresql(self, sample_tables):
        """Test import generation for PostgreSQL."""
        gen = DatabaseServerGenerator(
            DatabaseType.POSTGRESQL,
            "postgresql://localhost/test",
            tables=sample_tables,
        )
        code = gen._generate_imports()

        assert "import psycopg2" in code
        assert "RealDictCursor" in code

    def test_generate_db_setup_sqlite(self, sample_tables):
        """Test database setup for SQLite."""
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "data/mydb.sqlite",
            tables=sample_tables,
        )
        code = gen._generate_db_setup()

        assert "DATABASE_PATH" in code
        assert "sqlite3.connect" in code
        assert "Row" in code

    def test_generate_db_setup_postgresql(self, sample_tables):
        """Test database setup for PostgreSQL."""
        gen = DatabaseServerGenerator(
            DatabaseType.POSTGRESQL,
            "postgresql://localhost/test",
            tables=sample_tables,
        )
        code = gen._generate_db_setup()

        assert "DATABASE_URL" in code
        assert "psycopg2.connect" in code

    def test_generate_health_check(self, sample_tables):
        """Test health check generation."""
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=sample_tables,
        )
        code = gen._generate_health_check("TestServer")

        assert "def health_check()" in code
        assert "TestServer" in code
        assert "users" in code
        assert "posts" in code
        assert "tables_available" in code

    def test_generate_server_code_structure(self, sample_tables):
        """Test complete server code structure."""
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=sample_tables,
        )
        code = gen.generate_server_code("TestDBServer")

        # Check imports
        assert "import sqlite3" in code
        assert "FastMCP" in code

        # Check server setup
        assert 'FastMCP("TestDBServer"' in code

        # Check CRUD tools for users table
        assert "get_users" in code
        assert "list_users" in code
        assert "create_users" in code
        assert "update_users" in code
        assert "delete_users" in code

        # Check CRUD tools for posts table
        assert "get_posts" in code
        assert "list_posts" in code
        assert "create_posts" in code

        # Check main block
        assert 'if __name__ == "__main__"' in code

    def test_generate_get_tool(self, sample_tables):
        """Test GET tool generation."""
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=sample_tables,
        )
        pk = sample_tables[0].primary_key
        code = gen._generate_get_tool(sample_tables[0], "users", pk)

        assert "def get_users(id: int)" in code
        assert "SELECT * FROM users WHERE id = ?" in code
        assert "fetchone" in code

    def test_generate_list_tool(self, sample_tables):
        """Test LIST tool generation."""
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=sample_tables,
        )
        code = gen._generate_list_tool(sample_tables[0], "users")

        assert "def list_users(" in code
        assert "id: int | None = None" in code
        assert "name: str | None = None" in code
        assert "limit: int = 100" in code
        assert "offset: int = 0" in code
        assert "LIMIT" in code
        assert "OFFSET" in code

    def test_generate_create_tool(self, sample_tables):
        """Test CREATE tool generation."""
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=sample_tables,
        )
        code = gen._generate_create_tool(sample_tables[0], "users")

        assert "def create_users(" in code
        assert "INSERT INTO users" in code
        assert "lastrowid" in code

    def test_generate_update_tool(self, sample_tables):
        """Test UPDATE tool generation."""
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=sample_tables,
        )
        pk = sample_tables[0].primary_key
        code = gen._generate_update_tool(sample_tables[0], "users", pk)

        assert "def update_users(id: int" in code
        assert "UPDATE users SET" in code
        assert "rowcount" in code

    def test_generate_delete_tool(self, sample_tables):
        """Test DELETE tool generation."""
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=sample_tables,
        )
        pk = sample_tables[0].primary_key
        code = gen._generate_delete_tool(sample_tables[0], "users", pk)

        assert "def delete_users(id: int)" in code
        assert "DELETE FROM users WHERE id = ?" in code

    def test_safe_name(self, sample_tables):
        """Test table name sanitization."""
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=sample_tables,
        )

        assert gen._safe_name("users") == "users"
        assert gen._safe_name("user-posts") == "user_posts"
        assert gen._safe_name("1table") == "t_1table"
        assert gen._safe_name("Table Name") == "table_name"

    def test_get_tool_specs(self, sample_tables):
        """Test tool spec generation."""
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=sample_tables,
        )
        specs = gen.get_tool_specs()

        # Each table with PK should have 5 tools
        # users: get, list, create, update, delete = 5
        # posts: get, list, create, update, delete = 5
        assert len(specs) == 10

        spec_names = [s.name for s in specs]
        assert "get_users" in spec_names
        assert "list_users" in spec_names
        assert "create_users" in spec_names
        assert "update_users" in spec_names
        assert "delete_users" in spec_names

    def test_get_env_vars_sqlite(self, sample_tables):
        """Test environment variable list for SQLite."""
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=sample_tables,
        )
        env_vars = gen.get_env_vars()

        assert env_vars == ["DATABASE_PATH"]

    def test_get_env_vars_postgresql(self, sample_tables):
        """Test environment variable list for PostgreSQL."""
        gen = DatabaseServerGenerator(
            DatabaseType.POSTGRESQL,
            "postgresql://localhost/test",
            tables=sample_tables,
        )
        env_vars = gen.get_env_vars()

        assert env_vars == ["DATABASE_URL"]

    def test_postgresql_placeholders(self, sample_tables):
        """Test PostgreSQL uses %s placeholders."""
        gen = DatabaseServerGenerator(
            DatabaseType.POSTGRESQL,
            "postgresql://localhost/test",
            tables=sample_tables,
        )
        pk = sample_tables[0].primary_key
        code = gen._generate_get_tool(sample_tables[0], "users", pk)

        assert "%s" in code
        assert "?" not in code


class TestDatabaseIntegration:
    """Integration tests with real SQLite database."""

    @pytest.fixture
    def temp_db_with_data(self):
        """Create temp database with test data."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL,
                quantity INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        """
        )

        # Insert test data
        cursor.execute(
            "INSERT INTO products (name, price, quantity) VALUES (?, ?, ?)",
            ("Widget", 9.99, 100),
        )
        cursor.execute(
            "INSERT INTO products (name, price, quantity) VALUES (?, ?, ?)",
            ("Gadget", 19.99, 50),
        )

        conn.commit()
        conn.close()

        yield path
        os.unlink(path)

    def test_full_introspection(self, temp_db_with_data):
        """Test full database introspection."""
        introspector = DatabaseIntrospector(DatabaseType.SQLITE, temp_db_with_data)
        tables = introspector.get_tables()

        assert len(tables) == 1
        products = tables[0]
        assert products.name == "products"
        assert len(products.columns) == 5

        # Check column types
        price_col = next(c for c in products.columns if c.name == "price")
        assert price_col.to_python_type() == "float"

        qty_col = next(c for c in products.columns if c.name == "quantity")
        assert qty_col.to_python_type() == "int"

    def test_full_server_generation(self, temp_db_with_data):
        """Test full server code generation."""
        gen = DatabaseServerGenerator(DatabaseType.SQLITE, temp_db_with_data)
        code = gen.generate_server_code("ProductsServer")

        # Verify code compiles
        compile(code, "<string>", "exec")

        # Check all expected tools
        assert "get_products" in code
        assert "list_products" in code
        assert "create_products" in code
        assert "update_products" in code
        assert "delete_products" in code

        # Check proper type hints
        assert "price: float" in code
        assert "quantity: int" in code


class TestEdgeCases:
    """Tests for edge cases."""

    def test_table_without_primary_key(self):
        """Test handling table without primary key."""
        table = TableInfo(
            name="logs",
            columns=[
                ColumnInfo(name="message", data_type="TEXT"),
                ColumnInfo(name="timestamp", data_type="TEXT"),
            ],
        )
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=[table],
        )
        code = gen.generate_server_code("LogServer")

        # Should have list and create but not get, update, delete
        assert "list_logs" in code
        assert "create_logs" in code
        assert "get_logs" not in code
        assert "update_logs" not in code
        assert "delete_logs" not in code

    def test_empty_tables_list(self):
        """Test with no tables."""
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=[],
        )
        code = gen.generate_server_code("EmptyServer")

        assert "FastMCP" in code
        assert "DATABASE TOOLS" in code

    def test_special_table_names(self):
        """Test tables with special characters in names."""
        tables = [
            TableInfo(
                name="user-orders",
                columns=[
                    ColumnInfo(name="id", data_type="INTEGER", is_primary_key=True),
                ],
            ),
            TableInfo(
                name="order items",
                columns=[
                    ColumnInfo(name="id", data_type="INTEGER", is_primary_key=True),
                ],
            ),
        ]
        gen = DatabaseServerGenerator(
            DatabaseType.SQLITE,
            "test.db",
            tables=tables,
        )
        code = gen.generate_server_code("SpecialServer")

        # Names should be sanitized
        assert "get_user_orders" in code
        assert "get_order_items" in code
