# Security

MCP Tool Factory includes built-in security scanning and generates secure code patterns. This guide covers security features, scanning, and best practices.

## Overview

Security is integrated at multiple levels:

1. **Pre-generation** - Input validation and sanitization
2. **Generation** - Secure code patterns
3. **Post-generation** - Security scanning
4. **Runtime** - Input validation in generated code

---

## Security Scanning

Scan generated code for common vulnerabilities.

### CLI Usage

```bash
# Scan a generated server
mcp-factory scan ./servers/my-server/server.py

# Scan with verbose output
mcp-factory scan ./server.py --verbose

# Exit with error on findings
mcp-factory scan ./server.py --fail-on-finding
```

### Python API

```python
from tool_factory.security import scan_code, scan_file

# Scan code string
code = '''
password = "hardcoded123"
eval(user_input)
'''

issues = scan_code(code)
for issue in issues:
    print(f"[{issue.severity}] Line {issue.line}: {issue.message}")

# Scan file
issues = scan_file("./server.py")
```

### Output

```
[HIGH] Line 1: Hardcoded credential detected: password = "..."
[HIGH] Line 2: Use of eval() is dangerous and can lead to code injection
```

---

## Security Patterns Detected

### HIGH Severity

| Pattern | Risk | Remediation |
|---------|------|-------------|
| Hardcoded passwords | Credential exposure | Use environment variables |
| `eval()` usage | Code injection | Use `ast.literal_eval()` or avoid |
| `exec()` usage | Code injection | Avoid dynamic code execution |
| SQL string concatenation | SQL injection | Use parameterized queries |
| `pickle.loads()` | Arbitrary code execution | Use JSON or safe formats |
| `shell=True` in subprocess | Command injection | Use argument lists |

### MEDIUM Severity

| Pattern | Risk | Remediation |
|---------|------|-------------|
| Debug mode enabled | Information disclosure | Disable in production |
| Weak crypto (MD5, SHA1) | Hash collision | Use SHA-256 or better |
| HTTP URLs (not HTTPS) | Man-in-the-middle | Use HTTPS |
| `verify=False` in requests | Certificate bypass | Validate certificates |
| `random` for secrets | Predictable values | Use `secrets` module |

### LOW Severity

| Pattern | Risk | Remediation |
|---------|------|-------------|
| Print statements | Information leakage | Use proper logging |
| TODO/FIXME comments | Incomplete security | Address before production |
| Overly broad exceptions | Hidden errors | Catch specific exceptions |

---

## Security Issue Details

### SecurityIssue Model

```python
from dataclasses import dataclass

@dataclass
class SecurityIssue:
    severity: str      # "HIGH", "MEDIUM", "LOW"
    message: str       # Description of the issue
    line: int          # Line number (1-indexed)
    pattern: str       # Regex pattern that matched
    code_snippet: str  # The offending code
    remediation: str   # How to fix
```

### Example Usage

```python
from tool_factory.security import scan_code

code = '''
import os
password = os.environ.get("PASSWORD")
user_query = f"SELECT * FROM users WHERE id = {user_id}"
'''

issues = scan_code(code)
for issue in issues:
    print(f"Severity: {issue.severity}")
    print(f"Line: {issue.line}")
    print(f"Message: {issue.message}")
    print(f"Code: {issue.code_snippet}")
    print(f"Fix: {issue.remediation}")
    print()
```

Output:

```
Severity: HIGH
Line: 3
Message: Potential SQL injection - string formatting in query
Code: user_query = f"SELECT * FROM users WHERE id = {user_id}"
Fix: Use parameterized queries with placeholders
```

---

## Secure Code Generation

MCP Tool Factory generates secure code patterns by default.

### Parameterized Queries

Generated database tools use parameterized queries:

```python
# Generated code
@mcp.tool()
def get_user(user_id: int) -> dict:
    """Get user by ID."""
    conn = get_connection()
    # Parameterized query - no SQL injection
    cursor = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    )
    return dict(cursor.fetchone())
```

### Environment Variables for Secrets

API keys are never hardcoded:

```python
# Generated code
import os

AUTH_CONFIG = {
    "API_KEY": os.environ.get("API_KEY"),
}

def require_auth(key_name: str) -> str:
    """Get required auth - never expose in logs."""
    value = AUTH_CONFIG.get(key_name)
    if not value:
        raise ValueError(f"Missing required auth: {key_name}")
    return value
```

### Input Validation

Generated tools validate inputs:

```python
@mcp.tool()
def calculate(value: float) -> float:
    """Calculate with validated input."""
    import math
    if not math.isfinite(value):
        raise ValueError("Value must be finite (not NaN or infinity)")
    if value < 0:
        raise ValueError("Value must be non-negative")
    return math.sqrt(value)
```

### Safe HTTP Requests

HTTPS is enforced by default:

```python
import httpx

@mcp.tool()
def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS URLs are allowed")

    response = httpx.get(
        url,
        timeout=30.0,
        follow_redirects=True,
        # Certificate verification enabled by default
    )
    response.raise_for_status()
    return response.json()
```

---

## OWASP Top 10 Protection

### A01: Broken Access Control

Generated code includes authentication checks:

```python
def require_auth(key_name: str) -> str:
    """Require authentication before processing."""
    value = AUTH_CONFIG.get(key_name)
    if not value:
        raise ValueError(f"Authentication required: {key_name}")
    return value

@mcp.tool()
def get_protected_data() -> dict:
    require_auth("API_KEY")  # Auth check first
    # ... implementation
```

### A02: Cryptographic Failures

Use secure cryptographic practices:

```python
import hashlib
import secrets

# Generate secure tokens
def generate_token() -> str:
    return secrets.token_urlsafe(32)

# Use strong hashing
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        salt,
        100000
    ).hex()
```

### A03: Injection

Parameterized queries prevent injection:

```python
# SQL Injection prevention
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# Command injection prevention
import subprocess
subprocess.run(["ls", "-la", directory], check=True)  # No shell=True
```

### A04: Insecure Design

Rate limiting and input validation:

```python
from tool_factory.production import ProductionConfig

config = ProductionConfig(
    enable_rate_limiting=True,
    rate_limit_requests=100,
)
```

### A05: Security Misconfiguration

Secure defaults in generated code:

```python
# Debug disabled by default
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# Strict CORS (if applicable)
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",")
```

### A06: Vulnerable Components

Dependency scanning recommendations:

```bash
# Check for vulnerabilities
pip install safety
safety check -r requirements.txt

# Update dependencies
pip install --upgrade package-name
```

### A07: Authentication Failures

Secure authentication patterns:

```python
# Token-based auth with expiration
from datetime import datetime, timedelta

def validate_token(token: str) -> bool:
    payload = decode_token(token)
    if datetime.now() > payload["expires_at"]:
        raise ValueError("Token expired")
    return True
```

### A08: Data Integrity Failures

Validate all inputs:

```python
from pydantic import BaseModel, validator

class UserInput(BaseModel):
    name: str
    email: str

    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v
```

### A09: Logging Failures

Structured logging without sensitive data:

```python
# Never log secrets
StructuredLogger.info(
    "API request",
    endpoint="/users",
    # api_key=api_key,  # NEVER log this
    user_id=user_id,
)
```

### A10: Server-Side Request Forgery (SSRF)

URL validation:

```python
from urllib.parse import urlparse

def validate_url(url: str) -> bool:
    parsed = urlparse(url)

    # Only allow HTTPS
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS allowed")

    # Block internal IPs
    blocked = ["localhost", "127.0.0.1", "0.0.0.0", "10.", "192.168."]
    if any(parsed.netloc.startswith(b) for b in blocked):
        raise ValueError("Internal URLs not allowed")

    return True
```

---

## Secrets Management

### Environment Variables

```bash
# Development (.env)
export API_KEY=dev-key-xxxxx

# Production (secrets manager)
export API_KEY=$(vault read -field=value secret/api-key)
```

### Never Commit Secrets

```gitignore
# .gitignore
.env
.env.*
*.pem
*.key
secrets.json
```

### Docker Secrets

```yaml
# docker-compose.yml
services:
  mcp-server:
    environment:
      - API_KEY_FILE=/run/secrets/api_key
    secrets:
      - api_key

secrets:
  api_key:
    external: true
```

---

## CI/CD Security Integration

### GitHub Actions

```yaml
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: pip install mcp-tool-factory

      - name: Run security scan
        run: mcp-factory scan ./server.py --fail-on-finding

      - name: Run bandit
        run: |
          pip install bandit
          bandit -r . -ll

      - name: Check dependencies
        run: |
          pip install safety
          safety check -r requirements.txt
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: security-scan
        name: Security Scan
        entry: mcp-factory scan
        language: system
        files: \.py$
        pass_filenames: true
```

---

## Bandit Integration

For additional security scanning, integrate with Bandit:

```bash
# Install
pip install bandit

# Scan
bandit -r ./server.py -f json -o bandit-report.json

# With severity filter
bandit -r . -ll  # Only high severity
```

### Configuration

```ini
# .bandit
[bandit]
exclude_dirs = tests,venv
skips = B101,B601
```

---

## Security Checklist

### Before Deployment

- [ ] All API keys in environment variables
- [ ] No hardcoded credentials in code
- [ ] Security scan passes with no HIGH findings
- [ ] HTTPS enforced for all external calls
- [ ] Rate limiting configured
- [ ] Input validation on all tools
- [ ] Logging excludes sensitive data
- [ ] Dependencies checked for vulnerabilities
- [ ] Authentication required for sensitive operations

### Production Configuration

- [ ] Debug mode disabled
- [ ] Error messages don't expose internals
- [ ] Prometheus metrics secured
- [ ] Health check doesn't expose secrets
- [ ] Docker images from trusted sources
- [ ] Secrets managed securely

---

## Reporting Security Issues

If you discover a security vulnerability in MCP Tool Factory:

1. **Do not** open a public issue
2. Email security details to the maintainers
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work on a fix.

---

## Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://docs.python.org/3/library/security.html)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [MCP Security Best Practices](https://modelcontextprotocol.info/docs/best-practices/)
