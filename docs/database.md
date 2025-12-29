# Database CRUD Generation

Generate MCP servers with complete CRUD operations from database schemas. This guide covers SQLite and PostgreSQL support, customization options, and best practices.

## Overview

MCP Tool Factory can introspect database schemas and generate:

- **CRUD operations** for each table
- **Type-safe parameters** based on column types
- **Filtering and pagination** for list operations
- **Primary key handling** for get/update/delete
- **Foreign key awareness** for relationships

## Quick Start

```bash
# SQLite database
mcp-factory from-database ./myapp.db

# Specific tables
mcp-factory from-database ./data.db --tables users --tables orders

# PostgreSQL
mcp-factory from-database "postgresql://user:pass@localhost/db" --type postgresql
```

---

## Supported Databases

| Database | Support | Connection |
|----------|---------|------------|
| SQLite | Full | File path |
| PostgreSQL | Full | Connection string |
| MySQL | Planned | - |
| SQL Server | Planned | - |

---

## SQLite

### Basic Usage

```bash
mcp-factory from-database ./myapp.db
```

### With Specific Tables

```bash
mcp-factory from-database ./ecommerce.db \
  --tables products \
  --tables orders \
  --tables customers
```

### Custom Server Name

```bash
mcp-factory from-database ./data.db --name MyDataServer
```

### Environment Variable

The generated server uses `DATABASE_PATH`:

```bash
export DATABASE_PATH=./myapp.db
python server.py
```

---

## PostgreSQL

### Connection String

```bash
mcp-factory from-database "postgresql://user:password@localhost:5432/mydb" \
  --type postgresql
```

### Connection String Format

```
postgresql://[user[:password]@][host][:port]/database[?params]
```

**Examples:**

```bash
# Local with password
postgresql://postgres:secret@localhost:5432/mydb

# Remote with SSL
postgresql://user:pass@db.example.com:5432/mydb?sslmode=require

# Unix socket
postgresql:///mydb?host=/var/run/postgresql
```

### Environment Variable

The generated server uses `DATABASE_URL`:

```bash
export DATABASE_URL=postgresql://user:pass@localhost/mydb
python server.py
```

---

## Generated Tools

For each table, the following tools are generated:

### get_\<table\>

Get a single record by primary key.

```python
@mcp.tool()
def get_users(id: int) -> dict:
    """Get a user by ID.

    Args:
        id: The user's primary key

    Returns:
        User record or error if not found
    """
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM users WHERE id = ?", (id,))
    row = cursor.fetchone()
    if row:
        return dict(row)
    return {"error": "Not found"}
```

### list_\<table\>

List records with optional filtering and pagination.

```python
@mcp.tool()
def list_users(
    name: str = None,
    email: str = None,
    active: bool = None,
    limit: int = 100,
    offset: int = 0
) -> dict:
    """List users with optional filtering.

    Args:
        name: Filter by name (partial match)
        email: Filter by email (partial match)
        active: Filter by active status
        limit: Maximum records to return
        offset: Number of records to skip

    Returns:
        List of matching user records
    """
    query = "SELECT * FROM users WHERE 1=1"
    params = []

    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    if email:
        query += " AND email LIKE ?"
        params.append(f"%{email}%")
    if active is not None:
        query += " AND active = ?"
        params.append(active)

    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    conn = get_connection()
    cursor = conn.execute(query, params)
    return {"records": [dict(row) for row in cursor.fetchall()]}
```

### create_\<table\>

Insert a new record.

```python
@mcp.tool()
def create_users(
    name: str,
    email: str,
    active: bool = True
) -> dict:
    """Create a new user.

    Args:
        name: User's name (required)
        email: User's email (required)
        active: Whether user is active

    Returns:
        Created user record with ID
    """
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO users (name, email, active) VALUES (?, ?, ?)",
        (name, email, active)
    )
    conn.commit()
    return {"id": cursor.lastrowid, "name": name, "email": email, "active": active}
```

### update_\<table\>

Update an existing record.

```python
@mcp.tool()
def update_users(
    id: int,
    name: str = None,
    email: str = None,
    active: bool = None
) -> dict:
    """Update a user.

    Args:
        id: User ID (required)
        name: New name (optional)
        email: New email (optional)
        active: New active status (optional)

    Returns:
        Updated user record
    """
    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if email is not None:
        updates.append("email = ?")
        params.append(email)
    if active is not None:
        updates.append("active = ?")
        params.append(active)

    if not updates:
        return {"error": "No fields to update"}

    params.append(id)
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"

    conn = get_connection()
    conn.execute(query, params)
    conn.commit()

    return get_users(id)
```

### delete_\<table\>

Delete a record.

```python
@mcp.tool()
def delete_users(id: int) -> dict:
    """Delete a user.

    Args:
        id: User ID to delete

    Returns:
        Success status
    """
    conn = get_connection()
    cursor = conn.execute("DELETE FROM users WHERE id = ?", (id,))
    conn.commit()

    if cursor.rowcount > 0:
        return {"success": True, "deleted_id": id}
    return {"error": "Not found"}
```

---

## Type Mapping

### SQLite Types

| SQLite Type | Python Type | Tool Parameter |
|-------------|-------------|----------------|
| INTEGER | `int` | `id: int` |
| REAL | `float` | `price: float` |
| TEXT | `str` | `name: str` |
| BLOB | `bytes` | `data: bytes` |
| BOOLEAN | `bool` | `active: bool` |
| DATETIME | `str` | `created_at: str` |

### PostgreSQL Types

| PostgreSQL Type | Python Type | Tool Parameter |
|-----------------|-------------|----------------|
| integer, bigint | `int` | `id: int` |
| real, double | `float` | `price: float` |
| varchar, text | `str` | `name: str` |
| boolean | `bool` | `active: bool` |
| timestamp | `str` | `created_at: str` |
| date | `str` | `birth_date: str` |
| json, jsonb | `dict` | `metadata: dict` |
| uuid | `str` | `uuid: str` |
| array | `list` | `tags: list` |

---

## Primary Key Handling

### Single Primary Key

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT
);
```

```python
@mcp.tool()
def get_users(id: int) -> dict: ...

@mcp.tool()
def update_users(id: int, name: str = None) -> dict: ...

@mcp.tool()
def delete_users(id: int) -> dict: ...
```

### Composite Primary Key

```sql
CREATE TABLE order_items (
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    PRIMARY KEY (order_id, product_id)
);
```

```python
@mcp.tool()
def get_order_items(order_id: int, product_id: int) -> dict: ...

@mcp.tool()
def update_order_items(
    order_id: int,
    product_id: int,
    quantity: int = None
) -> dict: ...

@mcp.tool()
def delete_order_items(order_id: int, product_id: int) -> dict: ...
```

### No Primary Key

Tables without a primary key only get `list` and `create`:

```python
# No get, update, or delete (no unique identifier)
@mcp.tool()
def list_logs(...) -> dict: ...

@mcp.tool()
def create_logs(...) -> dict: ...
```

---

## Programmatic Usage

### Basic Usage

```python
from tool_factory.database import (
    DatabaseType,
    DatabaseIntrospector,
    DatabaseServerGenerator,
)

# Introspect database
introspector = DatabaseIntrospector(
    DatabaseType.SQLITE,
    "./myapp.db"
)

# Get all tables
tables = introspector.get_tables()

for table in tables:
    print(f"Table: {table.name}")
    print(f"  Primary Key: {table.primary_key}")
    for col in table.columns:
        print(f"  Column: {col.name} ({col.type})")
```

### Generate Server

```python
from tool_factory.database import (
    DatabaseType,
    DatabaseIntrospector,
    DatabaseServerGenerator,
)
from tool_factory.generators.server import ServerGenerator
from tool_factory.generators.docs import DocsGenerator
from tool_factory.models import GeneratedServer

# Introspect
introspector = DatabaseIntrospector(DatabaseType.SQLITE, "./myapp.db")
tables = introspector.get_tables()

# Filter tables
tables = [t for t in tables if t.name in ["users", "orders"]]

# Generate
generator = DatabaseServerGenerator(
    DatabaseType.SQLITE,
    "./myapp.db",
    tables,
)

server_code = generator.generate_server_code("MyDBServer")
tool_specs = generator.get_tool_specs()
env_vars = generator.get_env_vars()

# Create full server package
server_gen = ServerGenerator()
docs_gen = DocsGenerator()

result = GeneratedServer(
    name="MyDBServer",
    server_code=server_code,
    tool_specs=tool_specs,
    test_code=server_gen.generate_tests(tool_specs),
    dockerfile=server_gen.generate_dockerfile(tool_specs, env_vars),
    readme=docs_gen.generate_readme("MyDBServer", tool_specs),
    skill_file=docs_gen.generate_skill("MyDBServer", tool_specs),
    pyproject_toml=server_gen.generate_pyproject("MyDBServer", tool_specs),
    github_actions=server_gen.generate_github_actions("MyDBServer", tool_specs, env_vars),
)

result.write_to_directory("./servers/mydb")
```

### PostgreSQL Connection

```python
introspector = DatabaseIntrospector(
    DatabaseType.POSTGRESQL,
    "postgresql://user:pass@localhost:5432/mydb"
)

tables = introspector.get_tables()
```

---

## Example: E-commerce Database

### Schema

```sql
-- SQLite schema
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    stock INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    active BOOLEAN DEFAULT 1
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    total REAL NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
```

### Generate Server

```bash
mcp-factory from-database ./ecommerce.db --name EcommerceServer
```

### Generated Tools

**Products (5 tools):**
- `get_products(id: int)`
- `list_products(name: str = None, price: float = None, limit: int = 100, offset: int = 0)`
- `create_products(name: str, price: float, description: str = None, stock: int = 0)`
- `update_products(id: int, name: str = None, price: float = None, ...)`
- `delete_products(id: int)`

**Customers (5 tools):**
- `get_customers(id: int)`
- `list_customers(email: str = None, name: str = None, active: bool = None, ...)`
- `create_customers(email: str, name: str, active: bool = True)`
- `update_customers(id: int, email: str = None, name: str = None, ...)`
- `delete_customers(id: int)`

**Orders (5 tools):**
- `get_orders(id: int)`
- `list_orders(customer_id: int = None, status: str = None, ...)`
- `create_orders(customer_id: int, total: float, status: str = "pending")`
- `update_orders(id: int, status: str = None, total: float = None)`
- `delete_orders(id: int)`

**Order Items (5 tools):**
- `get_order_items(order_id: int, product_id: int)`
- `list_order_items(order_id: int = None, product_id: int = None, ...)`
- `create_order_items(order_id: int, product_id: int, quantity: int, price: float)`
- `update_order_items(order_id: int, product_id: int, quantity: int = None, price: float = None)`
- `delete_order_items(order_id: int, product_id: int)`

---

## Connection Management

### SQLite Connection Pooling

Generated servers use connection pooling for SQLite:

```python
import sqlite3
from contextlib import contextmanager

DATABASE_PATH = os.environ.get("DATABASE_PATH", "./database.db")

def get_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn
```

### PostgreSQL Connection Pooling

For PostgreSQL, connection pooling via `psycopg2.pool`:

```python
from psycopg2 import pool

DATABASE_URL = os.environ.get("DATABASE_URL")

connection_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=DATABASE_URL,
)

def get_connection():
    """Get connection from pool."""
    return connection_pool.getconn()

def release_connection(conn):
    """Release connection back to pool."""
    connection_pool.putconn(conn)
```

---

## Best Practices

### 1. Use Specific Tables

```bash
# Only generate tools for needed tables
mcp-factory from-database ./db.sqlite \
  --tables users \
  --tables products
```

### 2. Set Connection Limits

For PostgreSQL, configure pool size based on load:

```python
connection_pool = pool.ThreadedConnectionPool(
    minconn=2,
    maxconn=20,  # Adjust based on needs
    dsn=DATABASE_URL,
)
```

### 3. Handle Large Tables

For tables with many rows, always use pagination:

```python
# Default limit is 100
result = list_products(limit=50, offset=0)  # Page 1
result = list_products(limit=50, offset=50)  # Page 2
```

### 4. Validate Inputs

The generated tools include basic validation, but add more for production:

```python
@mcp.tool()
def create_users(name: str, email: str) -> dict:
    # Add validation
    if not name or len(name) < 2:
        return {"error": "Name must be at least 2 characters"}
    if not email or "@" not in email:
        return {"error": "Invalid email format"}

    # ... rest of implementation
```

---

## Troubleshooting

### "Could not connect to database"

**SQLite:**
- Check file path exists
- Check file permissions

```bash
ls -la ./myapp.db
chmod 644 ./myapp.db
```

**PostgreSQL:**
- Check connection string format
- Verify server is running
- Check network access

```bash
psql "postgresql://user:pass@localhost/mydb" -c "SELECT 1"
```

### "No tables found"

**Cause:** Database is empty or schema not accessible

**Solution:**
- Verify database has tables
- For PostgreSQL, check schema permissions

```sql
-- PostgreSQL: List tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public';

-- SQLite: List tables
SELECT name FROM sqlite_master WHERE type='table';
```

### "Primary key not detected"

**Cause:** Table lacks PRIMARY KEY constraint

**Solution:** Add primary key or use table without get/update/delete:

```sql
-- Add primary key
ALTER TABLE logs ADD COLUMN id INTEGER PRIMARY KEY;
```
