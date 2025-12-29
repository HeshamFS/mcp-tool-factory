"""Database schema introspection and CRUD tool generator.

Supports:
- SQLite (built-in, no external dependencies)
- PostgreSQL (requires psycopg2 or asyncpg)

Generates MCP tools for:
- get_<table>: Get single record by primary key
- list_<table>: List records with filtering and pagination
- create_<table>: Insert new record
- update_<table>: Update existing record
- delete_<table>: Delete record by primary key
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from tool_factory.models import ToolSpec


class DatabaseType(Enum):
    """Supported database types."""

    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


@dataclass
class ColumnInfo:
    """Information about a database column."""

    name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False
    default_value: Any = None
    foreign_key: str | None = None  # Format: "table.column"

    def to_python_type(self) -> str:
        """Convert SQL type to Python type hint."""
        type_lower = self.data_type.lower()

        if any(t in type_lower for t in ["int", "serial", "bigint", "smallint"]):
            return "int"
        elif any(
            t in type_lower for t in ["real", "double", "float", "decimal", "numeric"]
        ):
            return "float"
        elif any(t in type_lower for t in ["bool"]):
            return "bool"
        elif any(t in type_lower for t in ["json", "jsonb"]):
            return "dict"
        elif any(t in type_lower for t in ["array", "[]"]):
            return "list"
        else:
            return "str"

    def to_json_schema_type(self) -> str:
        """Convert SQL type to JSON Schema type."""
        py_type = self.to_python_type()
        type_map = {
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "dict": "object",
            "list": "array",
            "str": "string",
        }
        return type_map.get(py_type, "string")


@dataclass
class TableInfo:
    """Information about a database table."""

    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    schema: str = "public"

    @property
    def primary_key(self) -> ColumnInfo | None:
        """Get primary key column."""
        for col in self.columns:
            if col.is_primary_key:
                return col
        return None

    @property
    def non_pk_columns(self) -> list[ColumnInfo]:
        """Get non-primary key columns."""
        return [col for col in self.columns if not col.is_primary_key]


class DatabaseIntrospector:
    """Introspect database schema to extract table information."""

    def __init__(self, db_type: DatabaseType, connection_string: str) -> None:
        self.db_type = db_type
        self.connection_string = connection_string

    def get_tables(self) -> list[TableInfo]:
        """Get all tables from the database."""
        if self.db_type == DatabaseType.SQLITE:
            return self._get_sqlite_tables()
        elif self.db_type == DatabaseType.POSTGRESQL:
            return self._get_postgresql_tables()
        return []

    def _get_sqlite_tables(self) -> list[TableInfo]:
        """Get tables from SQLite database."""
        import sqlite3

        conn = sqlite3.connect(self.connection_string)
        cursor = conn.cursor()

        tables = []

        # Get all table names
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """
        )
        table_names = [row[0] for row in cursor.fetchall()]

        for table_name in table_names:
            # Get column info using PRAGMA
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for row in cursor.fetchall():
                # row: (cid, name, type, notnull, dflt_value, pk)
                columns.append(
                    ColumnInfo(
                        name=row[1],
                        data_type=row[2],
                        is_nullable=not bool(row[3]),
                        is_primary_key=bool(row[5]),
                        default_value=row[4],
                    )
                )

            # Get foreign keys
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            for fk_row in cursor.fetchall():
                # fk_row: (id, seq, table, from, to, on_update, on_delete, match)
                fk_table = fk_row[2]
                fk_from = fk_row[3]
                fk_to = fk_row[4]
                for col in columns:
                    if col.name == fk_from:
                        col.foreign_key = f"{fk_table}.{fk_to}"

            tables.append(TableInfo(name=table_name, columns=columns))

        conn.close()
        return tables

    def _get_postgresql_tables(self) -> list[TableInfo]:
        """Get tables from PostgreSQL database."""
        try:
            import psycopg2
        except ImportError:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. "
                "Install with: pip install psycopg2-binary"
            )

        conn = psycopg2.connect(self.connection_string)
        cursor = conn.cursor()

        tables = []

        # Get all tables in public schema
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        )
        table_names = [row[0] for row in cursor.fetchall()]

        for table_name in table_names:
            # Get column info
            cursor.execute(
                """
                SELECT
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_pk
                FROM information_schema.columns c
                LEFT JOIN (
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = %s AND tc.constraint_type = 'PRIMARY KEY'
                ) pk ON c.column_name = pk.column_name
                WHERE c.table_name = %s AND c.table_schema = 'public'
                ORDER BY c.ordinal_position
            """,
                (table_name, table_name),
            )

            columns = []
            for row in cursor.fetchall():
                columns.append(
                    ColumnInfo(
                        name=row[0],
                        data_type=row[1],
                        is_nullable=row[2] == "YES",
                        default_value=row[3],
                        is_primary_key=row[4],
                    )
                )

            # Get foreign keys
            cursor.execute(
                """
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table,
                    ccu.column_name AS foreign_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_name = %s AND tc.constraint_type = 'FOREIGN KEY'
            """,
                (table_name,),
            )

            for fk_row in cursor.fetchall():
                for col in columns:
                    if col.name == fk_row[0]:
                        col.foreign_key = f"{fk_row[1]}.{fk_row[2]}"

            tables.append(TableInfo(name=table_name, columns=columns, schema="public"))

        conn.close()
        return tables


class DatabaseServerGenerator:
    """Generate MCP server code for database CRUD operations."""

    def __init__(
        self,
        db_type: DatabaseType,
        connection_string: str,
        tables: list[TableInfo] | None = None,
    ) -> None:
        self.db_type = db_type
        self.connection_string = connection_string

        if tables:
            self.tables = tables
        else:
            introspector = DatabaseIntrospector(db_type, connection_string)
            self.tables = introspector.get_tables()

    def generate_server_code(self, server_name: str) -> str:
        """Generate complete MCP server code for database."""
        imports = self._generate_imports()
        db_setup = self._generate_db_setup()
        health_check = self._generate_health_check(server_name)

        tools = []
        for table in self.tables:
            tools.extend(self._generate_table_tools(table))

        return f'''"""Auto-generated MCP server for database operations."""

{imports}

mcp = FastMCP("{server_name}", json_response=True)

{db_setup}

{health_check}

# ============== DATABASE TOOLS ==============

{"".join(tools)}

# ============== MAIN ==============

if __name__ == "__main__":
    mcp.run(transport="stdio")
'''

    def _generate_imports(self) -> str:
        """Generate import statements."""
        base_imports = [
            "import os",
            "from datetime import datetime",
            "from typing import Any",
            "",
            "from mcp.server.fastmcp import FastMCP",
        ]

        if self.db_type == DatabaseType.SQLITE:
            base_imports.append("import sqlite3")
        elif self.db_type == DatabaseType.POSTGRESQL:
            base_imports.append("import psycopg2")
            base_imports.append("from psycopg2.extras import RealDictCursor")

        return "\n".join(base_imports)

    def _generate_db_setup(self) -> str:
        """Generate database connection setup."""
        if self.db_type == DatabaseType.SQLITE:
            # For SQLite, use environment variable or default path
            # Escape backslashes for Windows paths
            escaped_path = self.connection_string.replace("\\", "\\\\")
            return f'''
# Database configuration
DATABASE_PATH = os.environ.get("DATABASE_PATH", "{escaped_path}")


def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn
'''
        elif self.db_type == DatabaseType.POSTGRESQL:
            return '''
# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Missing required environment variable: DATABASE_URL")


def get_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
'''

    def _generate_health_check(self, server_name: str) -> str:
        """Generate health check tool."""
        table_list = ", ".join(f'"{t.name}"' for t in self.tables)

        return f'''
# ============== HEALTH CHECK ==============

@mcp.tool()
def health_check() -> dict:
    """
    Check database connectivity and list available tables.

    Returns:
        Health status including database info and tables
    """
    try:
        conn = get_connection()
        conn.close()
        status = "healthy"
        error = None
    except Exception as e:
        status = "unhealthy"
        error = str(e)

    return {{
        "status": status,
        "server": "{server_name}",
        "database_type": "{self.db_type.value}",
        "tables_available": [{table_list}],
        "timestamp": datetime.now().isoformat(),
        "error": error,
    }}

'''

    def _generate_table_tools(self, table: TableInfo) -> list[str]:
        """Generate CRUD tools for a table."""
        tools = []
        table_name = table.name
        safe_name = self._safe_name(table_name)
        pk = table.primary_key

        # get_<table> - Get by primary key
        if pk:
            tools.append(self._generate_get_tool(table, safe_name, pk))

        # list_<table> - List with filtering
        tools.append(self._generate_list_tool(table, safe_name))

        # create_<table> - Insert new record
        tools.append(self._generate_create_tool(table, safe_name))

        # update_<table> - Update by primary key
        if pk:
            tools.append(self._generate_update_tool(table, safe_name, pk))

        # delete_<table> - Delete by primary key
        if pk:
            tools.append(self._generate_delete_tool(table, safe_name, pk))

        return tools

    def _generate_get_tool(
        self, table: TableInfo, safe_name: str, pk: ColumnInfo
    ) -> str:
        """Generate get by ID tool."""
        pk_type = pk.to_python_type()
        placeholder = "?" if self.db_type == DatabaseType.SQLITE else "%s"

        return f'''
@mcp.tool()
def get_{safe_name}({pk.name}: {pk_type}) -> dict:
    """
    Get a {table.name} record by {pk.name}.

    Args:
        {pk.name}: The primary key value

    Returns:
        The {table.name} record or error
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM {table.name} WHERE {pk.name} = {placeholder}",
            ({pk.name},)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {{"data": dict(row)}}
        return {{"error": "{table.name} not found"}}
    except Exception as e:
        return {{"error": str(e)}}

'''

    def _generate_list_tool(self, table: TableInfo, safe_name: str) -> str:
        """Generate list with filtering tool."""
        # Build filter parameters
        filter_params = []
        filter_docs = []
        filter_conditions = []

        for col in table.columns:
            py_type = col.to_python_type()
            filter_params.append(f"{col.name}: {py_type} | None = None")
            filter_docs.append(f"        {col.name}: Filter by {col.name}")

            if self.db_type == DatabaseType.SQLITE:
                filter_conditions.append(
                    f"        if {col.name} is not None:\n"
                    f'            conditions.append("{col.name} = ?")\n'
                    f"            params.append({col.name})"
                )
            else:
                filter_conditions.append(
                    f"        if {col.name} is not None:\n"
                    f'            conditions.append("{col.name} = %s")\n'
                    f"            params.append({col.name})"
                )

        params_str = ", ".join(filter_params)
        docs_str = "\n".join(filter_docs)
        conditions_str = "\n".join(filter_conditions)

        return f'''
@mcp.tool()
def list_{safe_name}({params_str}, limit: int = 100, offset: int = 0) -> dict:
    """
    List {table.name} records with optional filtering.

    Args:
{docs_str}
        limit: Maximum records to return (default: 100)
        offset: Number of records to skip (default: 0)

    Returns:
        List of {table.name} records
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        conditions = []
        params = []

{conditions_str}

        query = "SELECT * FROM {table.name}"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += f" LIMIT {{limit}} OFFSET {{offset}}"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return {{"data": [dict(row) for row in rows], "count": len(rows)}}
    except Exception as e:
        return {{"error": str(e)}}

'''

    def _generate_create_tool(self, table: TableInfo, safe_name: str) -> str:
        """Generate create/insert tool."""
        # Get non-auto columns (exclude auto-increment PKs)
        insert_cols = []
        for col in table.columns:
            # Skip auto-increment primary keys:
            # - SQLite: INTEGER PRIMARY KEY is auto-increment by default
            # - PostgreSQL: SERIAL types are auto-increment
            if col.is_primary_key:
                type_lower = col.data_type.lower()
                if "int" in type_lower or "serial" in type_lower:
                    continue
            insert_cols.append(col)

        # Build parameters - required params first, then optional
        required_params = []
        optional_params = []
        docs = []
        col_names = []

        for col in insert_cols:
            py_type = col.to_python_type()
            if col.is_nullable or col.default_value:
                optional_params.append(f"{col.name}: {py_type} | None = None")
            else:
                required_params.append(f"{col.name}: {py_type}")
            docs.append(f"        {col.name}: {col.data_type}")
            col_names.append(col.name)

        # Required params must come before optional
        params = required_params + optional_params
        params_str = ", ".join(params)
        docs_str = "\n".join(docs)
        cols_str = ", ".join(col_names)

        if self.db_type == DatabaseType.SQLITE:
            placeholders = ", ".join(["?"] * len(col_names))
            values_code = f"({', '.join(col_names)},)"
        else:
            placeholders = ", ".join(["%s"] * len(col_names))
            values_code = f"({', '.join(col_names)},)"

        return f'''
@mcp.tool()
def create_{safe_name}({params_str}) -> dict:
    """
    Create a new {table.name} record.

    Args:
{docs_str}

    Returns:
        The created record ID or error
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO {table.name} ({cols_str}) VALUES ({placeholders})",
            {values_code}
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()

        return {{"success": True, "id": new_id}}
    except Exception as e:
        return {{"error": str(e)}}

'''

    def _generate_update_tool(
        self, table: TableInfo, safe_name: str, pk: ColumnInfo
    ) -> str:
        """Generate update tool."""
        # Update non-PK columns
        update_cols = [col for col in table.columns if not col.is_primary_key]

        params = [f"{pk.name}: {pk.to_python_type()}"]
        docs = [f"        {pk.name}: Primary key of record to update"]
        set_clauses = []

        for col in update_cols:
            py_type = col.to_python_type()
            params.append(f"{col.name}: {py_type} | None = None")
            docs.append(f"        {col.name}: New value for {col.name}")

            placeholder = "?" if self.db_type == DatabaseType.SQLITE else "%s"
            set_clauses.append(
                f"        if {col.name} is not None:\n"
                f'            updates.append("{col.name} = {placeholder}")\n'
                f"            params.append({col.name})"
            )

        params_str = ", ".join(params)
        docs_str = "\n".join(docs)
        set_code = "\n".join(set_clauses)
        placeholder = "?" if self.db_type == DatabaseType.SQLITE else "%s"

        return f'''
@mcp.tool()
def update_{safe_name}({params_str}) -> dict:
    """
    Update a {table.name} record.

    Args:
{docs_str}

    Returns:
        Success status or error
    """
    try:
        updates = []
        params = []

{set_code}

        if not updates:
            return {{"error": "No fields to update"}}

        params.append({pk.name})

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE {table.name} SET {{', '.join(updates)}} WHERE {pk.name} = {placeholder}",
            params
        )
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()

        return {{"success": True, "rows_affected": rows_affected}}
    except Exception as e:
        return {{"error": str(e)}}

'''

    def _generate_delete_tool(
        self, table: TableInfo, safe_name: str, pk: ColumnInfo
    ) -> str:
        """Generate delete tool."""
        pk_type = pk.to_python_type()
        placeholder = "?" if self.db_type == DatabaseType.SQLITE else "%s"

        return f'''
@mcp.tool()
def delete_{safe_name}({pk.name}: {pk_type}) -> dict:
    """
    Delete a {table.name} record.

    Args:
        {pk.name}: Primary key of record to delete

    Returns:
        Success status or error
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM {table.name} WHERE {pk.name} = {placeholder}",
            ({pk.name},)
        )
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()

        return {{"success": True, "rows_affected": rows_affected}}
    except Exception as e:
        return {{"error": str(e)}}

'''

    def _safe_name(self, name: str) -> str:
        """Convert table name to safe Python identifier."""
        # Replace non-alphanumeric with underscore
        safe = re.sub(r"[^a-zA-Z0-9]", "_", name)
        # Ensure starts with letter
        if safe and safe[0].isdigit():
            safe = f"t_{safe}"
        return safe.lower()

    def get_tool_specs(self) -> list[ToolSpec]:
        """Get ToolSpec objects for documentation."""
        specs = []

        for table in self.tables:
            safe_name = self._safe_name(table.name)
            pk = table.primary_key

            # get_<table>
            if pk:
                specs.append(
                    ToolSpec(
                        name=f"get_{safe_name}",
                        description=f"Get a {table.name} record by {pk.name}",
                        input_schema={
                            "type": "object",
                            "properties": {
                                pk.name: {
                                    "type": pk.to_json_schema_type(),
                                    "description": "Primary key value",
                                },
                            },
                            "required": [pk.name],
                        },
                        dependencies=(
                            ["sqlite3"]
                            if self.db_type == DatabaseType.SQLITE
                            else ["psycopg2"]
                        ),
                    )
                )

            # list_<table>
            list_props = {}
            for col in table.columns:
                list_props[col.name] = {
                    "type": col.to_json_schema_type(),
                    "description": f"Filter by {col.name}",
                }
            list_props["limit"] = {
                "type": "integer",
                "description": "Max records",
                "default": 100,
            }
            list_props["offset"] = {
                "type": "integer",
                "description": "Records to skip",
                "default": 0,
            }

            specs.append(
                ToolSpec(
                    name=f"list_{safe_name}",
                    description=f"List {table.name} records with optional filtering",
                    input_schema={"type": "object", "properties": list_props},
                    dependencies=(
                        ["sqlite3"]
                        if self.db_type == DatabaseType.SQLITE
                        else ["psycopg2"]
                    ),
                )
            )

            # create_<table>
            create_props = {}
            create_required = []
            for col in table.columns:
                if col.is_primary_key:
                    continue
                create_props[col.name] = {
                    "type": col.to_json_schema_type(),
                    "description": col.data_type,
                }
                if not col.is_nullable and not col.default_value:
                    create_required.append(col.name)

            specs.append(
                ToolSpec(
                    name=f"create_{safe_name}",
                    description=f"Create a new {table.name} record",
                    input_schema={
                        "type": "object",
                        "properties": create_props,
                        "required": create_required,
                    },
                    dependencies=(
                        ["sqlite3"]
                        if self.db_type == DatabaseType.SQLITE
                        else ["psycopg2"]
                    ),
                )
            )

            # update_<table>
            if pk:
                update_props = {pk.name: {"type": pk.to_json_schema_type()}}
                for col in table.non_pk_columns:
                    update_props[col.name] = {"type": col.to_json_schema_type()}

                specs.append(
                    ToolSpec(
                        name=f"update_{safe_name}",
                        description=f"Update a {table.name} record",
                        input_schema={
                            "type": "object",
                            "properties": update_props,
                            "required": [pk.name],
                        },
                        dependencies=(
                            ["sqlite3"]
                            if self.db_type == DatabaseType.SQLITE
                            else ["psycopg2"]
                        ),
                    )
                )

                # delete_<table>
                specs.append(
                    ToolSpec(
                        name=f"delete_{safe_name}",
                        description=f"Delete a {table.name} record",
                        input_schema={
                            "type": "object",
                            "properties": {pk.name: {"type": pk.to_json_schema_type()}},
                            "required": [pk.name],
                        },
                        dependencies=(
                            ["sqlite3"]
                            if self.db_type == DatabaseType.SQLITE
                            else ["psycopg2"]
                        ),
                    )
                )

        return specs

    def get_env_vars(self) -> list[str]:
        """Get required environment variables."""
        if self.db_type == DatabaseType.SQLITE:
            return ["DATABASE_PATH"]
        elif self.db_type == DatabaseType.POSTGRESQL:
            return ["DATABASE_URL"]
        return []
