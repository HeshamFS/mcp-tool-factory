# Authentication

MCP Tool Factory supports multiple authentication methods for generated servers. This guide covers API keys, OAuth2/PKCE, and custom authentication patterns.

## Overview

| Auth Type | Use Case | Complexity |
|-----------|----------|------------|
| API Key | Simple API access | Low |
| Bearer Token | JWT/OAuth tokens | Low |
| OAuth2/PKCE | Secure user authorization | High |
| Basic Auth | Legacy systems | Low |
| Custom | Specialized needs | Variable |

---

## API Key Authentication

The simplest form of authentication using environment variables.

### CLI Usage

```bash
# Single API key
mcp-factory generate "Weather API" --auth WEATHER_API_KEY

# Multiple API keys
mcp-factory generate "Multi-service API" \
  --auth PRIMARY_API_KEY \
  --auth BACKUP_API_KEY \
  --auth ANALYTICS_KEY
```

### Generated Code

```python
import os

# Auth configuration
AUTH_CONFIG = {
    "WEATHER_API_KEY": os.environ.get("WEATHER_API_KEY"),
    "BACKUP_API_KEY": os.environ.get("BACKUP_API_KEY"),
}

def require_auth(key_name: str) -> str:
    """Get required authentication credential.

    Args:
        key_name: Name of the environment variable

    Returns:
        The credential value

    Raises:
        ValueError: If credential is not configured
    """
    value = AUTH_CONFIG.get(key_name)
    if not value:
        raise ValueError(f"Missing required auth: {key_name}. Set {key_name} environment variable.")
    return value

@mcp.tool()
def get_weather(city: str) -> dict:
    """Get weather for a city."""
    api_key = require_auth("WEATHER_API_KEY")
    response = httpx.get(
        "https://api.weather.com/v1/current",
        headers={"X-API-Key": api_key},
        params={"city": city}
    )
    return response.json()
```

### Running the Server

```bash
export WEATHER_API_KEY=your-api-key-here
python server.py
```

### Docker Usage

```dockerfile
# Dockerfile
ENV WEATHER_API_KEY=""

# docker-compose.yml
services:
  mcp-server:
    environment:
      - WEATHER_API_KEY=${WEATHER_API_KEY}
```

```bash
WEATHER_API_KEY=xxx docker-compose up
```

---

## Health Check with Auth Status

Generated servers include a health check that reports auth status:

```python
@mcp.tool()
def health_check() -> dict:
    """Check server health and authentication status.

    Returns:
        Health status including auth configuration
    """
    auth_status = {}
    for key in AUTH_CONFIG:
        auth_status[key] = "configured" if AUTH_CONFIG[key] else "missing"

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "auth_config": auth_status,
    }
```

**Example Response:**

```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00",
  "auth_config": {
    "WEATHER_API_KEY": "configured",
    "BACKUP_API_KEY": "missing"
  }
}
```

---

## OAuth2/PKCE Authentication

For secure user authorization flows, use the built-in OAuth2/PKCE support.

### OAuth2 Configuration

```python
from tool_factory.auth import OAuth2Config, OAuth2Flow

config = OAuth2Config(
    client_id="your-client-id",
    client_secret="your-client-secret",  # Optional for public clients
    authorization_url="https://auth.example.com/authorize",
    token_url="https://auth.example.com/token",
    scopes=["read", "write"],
    redirect_uri="http://localhost:8080/callback",
)
```

### PKCE (Proof Key for Code Exchange)

PKCE is recommended for public clients (desktop/mobile apps) per RFC 7636:

```python
from tool_factory.auth import PKCECodeVerifier

# Generate PKCE verifier and challenge
verifier = PKCECodeVerifier.generate()

print(f"Verifier: {verifier.verifier}")  # Store securely
print(f"Challenge: {verifier.challenge}")  # Send in auth request
print(f"Method: {verifier.method}")  # "S256"
```

### Complete OAuth2/PKCE Flow

```python
from tool_factory.auth import (
    OAuth2Config,
    OAuth2Flow,
    PKCECodeVerifier,
)

# 1. Configure OAuth2
config = OAuth2Config(
    client_id="your-client-id",
    authorization_url="https://auth.example.com/authorize",
    token_url="https://auth.example.com/token",
    scopes=["read", "write"],
    redirect_uri="http://localhost:8080/callback",
)

# 2. Generate PKCE verifier
verifier = PKCECodeVerifier.generate()

# 3. Build authorization URL
flow = OAuth2Flow(config)
auth_url = flow.get_authorization_url(
    state="random-state-string",
    code_challenge=verifier.challenge,
    code_challenge_method="S256",
)

print(f"Open in browser: {auth_url}")

# 4. User authorizes and is redirected with code
# http://localhost:8080/callback?code=AUTH_CODE&state=random-state-string

# 5. Exchange code for token
tokens = await flow.exchange_code(
    code="AUTH_CODE",
    code_verifier=verifier.verifier,
)

print(f"Access Token: {tokens.access_token}")
print(f"Refresh Token: {tokens.refresh_token}")
print(f"Expires In: {tokens.expires_in}")
```

### Token Refresh

```python
# Refresh expired token
new_tokens = await flow.refresh_token(tokens.refresh_token)
```

---

## OAuth2 Providers

Built-in configurations for popular OAuth2 providers.

### GitHub

```python
from tool_factory.auth.providers import GitHubOAuth

github = GitHubOAuth(
    client_id="your-github-client-id",
    client_secret="your-github-secret",
    scopes=["read:user", "repo"],
)

auth_url = github.get_authorization_url()
tokens = await github.exchange_code(code)
```

### Google

```python
from tool_factory.auth.providers import GoogleOAuth

google = GoogleOAuth(
    client_id="your-google-client-id",
    client_secret="your-google-secret",
    scopes=["openid", "email", "profile"],
)
```

### Azure AD / Entra ID

```python
from tool_factory.auth.providers import AzureADOAuth

azure = AzureADOAuth(
    client_id="your-azure-client-id",
    tenant_id="your-tenant-id",
    scopes=["User.Read"],
)
```

### Custom Provider

```python
from tool_factory.auth.providers import CustomOAuth

custom = CustomOAuth(
    name="MyProvider",
    authorization_url="https://auth.example.com/authorize",
    token_url="https://auth.example.com/token",
    client_id="client-id",
    client_secret="client-secret",
    scopes=["custom:scope"],
)
```

---

## Bearer Token Authentication

For JWT or OAuth2 bearer tokens:

```python
@mcp.tool()
def get_protected_data() -> dict:
    """Get data from protected endpoint."""
    token = require_auth("BEARER_TOKEN")
    response = httpx.get(
        "https://api.example.com/protected",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()
```

---

## Basic Authentication

For legacy systems requiring HTTP Basic auth:

```python
import base64

@mcp.tool()
def get_legacy_data() -> dict:
    """Get data from legacy API."""
    username = require_auth("API_USERNAME")
    password = require_auth("API_PASSWORD")

    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()

    response = httpx.get(
        "https://legacy.example.com/data",
        headers={"Authorization": f"Basic {credentials}"}
    )
    return response.json()
```

---

## Token Storage

### Environment Variables (Recommended for CLI)

```bash
export ACCESS_TOKEN=your-token
export REFRESH_TOKEN=your-refresh-token
```

### Secure File Storage

```python
import json
from pathlib import Path

TOKEN_FILE = Path.home() / ".mcp-tokens" / "tokens.json"

def save_tokens(tokens: dict):
    """Save tokens securely."""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens))
    TOKEN_FILE.chmod(0o600)  # Only user can read/write

def load_tokens() -> dict | None:
    """Load saved tokens."""
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None
```

### Keychain (macOS)

```python
import keyring

def save_token(service: str, token: str):
    keyring.set_password(service, "access_token", token)

def get_token(service: str) -> str:
    return keyring.get_password(service, "access_token")
```

---

## Automatic Token Refresh

Implement automatic token refresh for long-running servers:

```python
from datetime import datetime, timedelta
import threading

class TokenManager:
    def __init__(self, flow: OAuth2Flow, refresh_token: str):
        self.flow = flow
        self.access_token = None
        self.refresh_token = refresh_token
        self.expires_at = None
        self._lock = threading.Lock()

    async def get_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        with self._lock:
            if self._is_expired():
                await self._refresh()
            return self.access_token

    def _is_expired(self) -> bool:
        if not self.expires_at:
            return True
        # Refresh 5 minutes before expiry
        return datetime.now() > self.expires_at - timedelta(minutes=5)

    async def _refresh(self):
        tokens = await self.flow.refresh_token(self.refresh_token)
        self.access_token = tokens.access_token
        self.refresh_token = tokens.refresh_token
        self.expires_at = datetime.now() + timedelta(seconds=tokens.expires_in)
```

---

## Security Best Practices

### 1. Use PKCE for Public Clients

Always use PKCE for desktop, mobile, or CLI applications:

```python
verifier = PKCECodeVerifier.generate()
# Use S256 method (SHA256), not plain
assert verifier.method == "S256"
```

### 2. Validate State Parameter

Prevent CSRF attacks by validating the state parameter:

```python
import secrets

# Generate state
state = secrets.token_urlsafe(32)
# Store in session/memory

# On callback, verify state matches
if callback_state != stored_state:
    raise ValueError("Invalid state - possible CSRF attack")
```

### 3. Use Short-Lived Tokens

Configure short expiration for access tokens:

```python
# Server-side configuration
ACCESS_TOKEN_EXPIRY = 3600  # 1 hour
REFRESH_TOKEN_EXPIRY = 604800  # 7 days
```

### 4. Secure Token Storage

Never store tokens in:
- Plain text files without encryption
- Git repositories
- Logs or error messages
- Client-side storage (cookies, localStorage)

### 5. Rotate Refresh Tokens

Implement refresh token rotation:

```python
async def _refresh(self):
    tokens = await self.flow.refresh_token(self.refresh_token)
    # Old refresh token is now invalid
    self.refresh_token = tokens.refresh_token  # Save new one
```

---

## Environment Configuration

### Development

```bash
# .env.development
WEATHER_API_KEY=dev-key-xxxxx
OAUTH_CLIENT_ID=dev-client
```

### Production

```bash
# Use secrets management
export WEATHER_API_KEY=$(vault read -field=value secret/weather-api)
```

### Docker

```yaml
# docker-compose.yml
services:
  mcp-server:
    environment:
      - WEATHER_API_KEY=${WEATHER_API_KEY}
    secrets:
      - oauth_client_secret

secrets:
  oauth_client_secret:
    external: true
```

---

## Troubleshooting

### "Missing required auth"

**Cause:** Environment variable not set

**Solution:**

```bash
# Check if set
echo $WEATHER_API_KEY

# Set it
export WEATHER_API_KEY=your-key
```

### "Invalid token"

**Cause:** Token expired or malformed

**Solution:**
- Refresh the token
- Re-authenticate
- Check token format

### "PKCE verification failed"

**Cause:** Verifier doesn't match challenge

**Solution:**
- Store verifier before redirect
- Use same verifier in token exchange

```python
# WRONG: Generating new verifier
tokens = await flow.exchange_code(code, PKCECodeVerifier.generate().verifier)

# RIGHT: Use original verifier
tokens = await flow.exchange_code(code, original_verifier.verifier)
```

### "State mismatch"

**Cause:** CSRF protection triggered

**Solution:**
- Store state in session
- Verify state on callback

```python
# Store before redirect
session['oauth_state'] = state

# Verify on callback
if request.args['state'] != session['oauth_state']:
    abort(403, "State mismatch")
```
