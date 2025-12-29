# Examples

Practical examples of using MCP Tool Factory for common use cases.

## Quick Reference

| Example | Description | Complexity |
|---------|-------------|------------|
| [Weather API](#weather-api) | Simple REST API | Beginner |
| [GitHub Tools](#github-tools) | OAuth authentication | Intermediate |
| [E-commerce CRUD](#e-commerce-crud) | Database operations | Intermediate |
| [Stripe Payments](#stripe-payments) | OpenAPI import | Intermediate |
| [Multi-Service](#multi-service-aggregator) | Multiple APIs | Advanced |
| [Production Server](#production-server) | Full production setup | Advanced |

---

## Weather API

A simple weather API wrapper with API key authentication.

### Generate

```bash
mcp-factory generate \
  "Weather API tools:
   - get_current_weather(city) - returns temperature, conditions, humidity
   - get_forecast(city, days) - returns multi-day forecast
   - get_weather_alerts(city) - returns active weather alerts" \
  --name WeatherServer \
  --auth WEATHER_API_KEY \
  --output ./servers/weather
```

### Generated Server

```python
from mcp.server.fastmcp import FastMCP
import httpx
import os

mcp = FastMCP("WeatherServer")

BASE_URL = "https://api.weatherapi.com/v1"

AUTH_CONFIG = {
    "WEATHER_API_KEY": os.environ.get("WEATHER_API_KEY"),
}

def require_auth(key_name: str) -> str:
    value = AUTH_CONFIG.get(key_name)
    if not value:
        raise ValueError(f"Missing required auth: {key_name}")
    return value

@mcp.tool()
def get_current_weather(city: str) -> dict:
    """Get current weather conditions for a city.

    Args:
        city: City name (e.g., "Seattle", "New York")

    Returns:
        Current temperature, conditions, and humidity
    """
    api_key = require_auth("WEATHER_API_KEY")
    response = httpx.get(
        f"{BASE_URL}/current.json",
        params={"key": api_key, "q": city}
    )
    response.raise_for_status()
    data = response.json()
    return {
        "city": data["location"]["name"],
        "temperature_f": data["current"]["temp_f"],
        "temperature_c": data["current"]["temp_c"],
        "condition": data["current"]["condition"]["text"],
        "humidity": data["current"]["humidity"],
    }

@mcp.tool()
def get_forecast(city: str, days: int = 3) -> dict:
    """Get weather forecast for a city.

    Args:
        city: City name
        days: Number of days (1-7)

    Returns:
        Multi-day weather forecast
    """
    if days < 1 or days > 7:
        raise ValueError("Days must be between 1 and 7")

    api_key = require_auth("WEATHER_API_KEY")
    response = httpx.get(
        f"{BASE_URL}/forecast.json",
        params={"key": api_key, "q": city, "days": days}
    )
    response.raise_for_status()
    data = response.json()

    forecast = []
    for day in data["forecast"]["forecastday"]:
        forecast.append({
            "date": day["date"],
            "max_temp_f": day["day"]["maxtemp_f"],
            "min_temp_f": day["day"]["mintemp_f"],
            "condition": day["day"]["condition"]["text"],
            "chance_of_rain": day["day"]["daily_chance_of_rain"],
        })

    return {"city": city, "forecast": forecast}

@mcp.tool()
def get_weather_alerts(city: str) -> dict:
    """Get active weather alerts for a city.

    Args:
        city: City name

    Returns:
        List of active weather alerts
    """
    api_key = require_auth("WEATHER_API_KEY")
    response = httpx.get(
        f"{BASE_URL}/forecast.json",
        params={"key": api_key, "q": city, "alerts": "yes"}
    )
    response.raise_for_status()
    data = response.json()

    alerts = data.get("alerts", {}).get("alert", [])
    return {
        "city": city,
        "alert_count": len(alerts),
        "alerts": [
            {
                "headline": alert.get("headline"),
                "severity": alert.get("severity"),
                "event": alert.get("event"),
            }
            for alert in alerts
        ],
    }

if __name__ == "__main__":
    mcp.run()
```

### Usage

```bash
# Set API key
export WEATHER_API_KEY=your-key-here

# Run server
python server.py
```

---

## GitHub Tools

GitHub API integration with OAuth authentication.

### Generate

```bash
mcp-factory generate \
  "GitHub tools with OAuth:
   - list_repos(username) - list user repositories
   - get_repo(owner, repo) - get repository details
   - list_issues(owner, repo, state) - list issues
   - create_issue(owner, repo, title, body) - create new issue
   - search_code(query, language) - search code across GitHub" \
  --name GitHubServer \
  --auth GITHUB_TOKEN \
  --web-search \
  --output ./servers/github
```

### Generated Server

```python
from mcp.server.fastmcp import FastMCP
import httpx
import os

mcp = FastMCP("GitHubServer")

BASE_URL = "https://api.github.com"

AUTH_CONFIG = {
    "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN"),
}

def require_auth(key_name: str) -> str:
    value = AUTH_CONFIG.get(key_name)
    if not value:
        raise ValueError(f"Missing required auth: {key_name}")
    return value

def get_headers() -> dict:
    """Get authenticated headers."""
    token = require_auth("GITHUB_TOKEN")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

@mcp.tool()
def list_repos(username: str, per_page: int = 30) -> dict:
    """List repositories for a GitHub user.

    Args:
        username: GitHub username
        per_page: Results per page (max 100)

    Returns:
        List of repositories with name, description, stars
    """
    response = httpx.get(
        f"{BASE_URL}/users/{username}/repos",
        headers=get_headers(),
        params={"per_page": min(per_page, 100), "sort": "updated"}
    )
    response.raise_for_status()

    repos = []
    for repo in response.json():
        repos.append({
            "name": repo["name"],
            "full_name": repo["full_name"],
            "description": repo["description"],
            "stars": repo["stargazers_count"],
            "language": repo["language"],
            "url": repo["html_url"],
        })

    return {"username": username, "repos": repos}

@mcp.tool()
def get_repo(owner: str, repo: str) -> dict:
    """Get detailed information about a repository.

    Args:
        owner: Repository owner
        repo: Repository name

    Returns:
        Repository details including stats
    """
    response = httpx.get(
        f"{BASE_URL}/repos/{owner}/{repo}",
        headers=get_headers()
    )
    response.raise_for_status()
    data = response.json()

    return {
        "name": data["name"],
        "full_name": data["full_name"],
        "description": data["description"],
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "open_issues": data["open_issues_count"],
        "language": data["language"],
        "topics": data.get("topics", []),
        "default_branch": data["default_branch"],
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
    }

@mcp.tool()
def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 30
) -> dict:
    """List issues for a repository.

    Args:
        owner: Repository owner
        repo: Repository name
        state: Issue state (open, closed, all)
        per_page: Results per page (max 100)

    Returns:
        List of issues with title, state, labels
    """
    if state not in ["open", "closed", "all"]:
        raise ValueError("State must be 'open', 'closed', or 'all'")

    response = httpx.get(
        f"{BASE_URL}/repos/{owner}/{repo}/issues",
        headers=get_headers(),
        params={"state": state, "per_page": min(per_page, 100)}
    )
    response.raise_for_status()

    issues = []
    for issue in response.json():
        issues.append({
            "number": issue["number"],
            "title": issue["title"],
            "state": issue["state"],
            "labels": [l["name"] for l in issue.get("labels", [])],
            "author": issue["user"]["login"],
            "created_at": issue["created_at"],
            "url": issue["html_url"],
        })

    return {"repo": f"{owner}/{repo}", "state": state, "issues": issues}

@mcp.tool()
def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: list = None
) -> dict:
    """Create a new issue in a repository.

    Args:
        owner: Repository owner
        repo: Repository name
        title: Issue title
        body: Issue body (markdown supported)
        labels: List of label names

    Returns:
        Created issue details
    """
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels

    response = httpx.post(
        f"{BASE_URL}/repos/{owner}/{repo}/issues",
        headers=get_headers(),
        json=payload
    )
    response.raise_for_status()
    data = response.json()

    return {
        "number": data["number"],
        "title": data["title"],
        "url": data["html_url"],
        "state": data["state"],
    }

@mcp.tool()
def search_code(
    query: str,
    language: str = None,
    per_page: int = 30
) -> dict:
    """Search code across GitHub repositories.

    Args:
        query: Search query
        language: Filter by programming language
        per_page: Results per page (max 100)

    Returns:
        List of matching code files
    """
    q = query
    if language:
        q += f" language:{language}"

    response = httpx.get(
        f"{BASE_URL}/search/code",
        headers=get_headers(),
        params={"q": q, "per_page": min(per_page, 100)}
    )
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("items", []):
        results.append({
            "name": item["name"],
            "path": item["path"],
            "repository": item["repository"]["full_name"],
            "url": item["html_url"],
        })

    return {
        "query": query,
        "total_count": data.get("total_count", 0),
        "results": results,
    }

if __name__ == "__main__":
    mcp.run()
```

---

## E-commerce CRUD

Generate CRUD operations from a database schema.

### Database Schema

```sql
-- ecommerce.db
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    stock INTEGER DEFAULT 0,
    category TEXT,
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
```

### Generate

```bash
# Generate CRUD from database
mcp-factory from-database ./ecommerce.db \
  --name EcommerceServer \
  --tables products --tables customers --tables orders \
  --output ./servers/ecommerce
```

### Generated Tools

- `get_products(id)` - Get product by ID
- `list_products(name, category, limit, offset)` - List products with filters
- `create_products(name, price, description, stock, category)` - Create product
- `update_products(id, name, price, ...)` - Update product
- `delete_products(id)` - Delete product
- Same CRUD operations for `customers` and `orders`

### Usage

```bash
export DATABASE_PATH=./ecommerce.db
python server.py
```

---

## Stripe Payments

Import from Stripe's OpenAPI specification.

### Download Spec

```bash
curl -o stripe-api.yaml https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.yaml
```

### Generate

```bash
mcp-factory from-openapi ./stripe-api.yaml \
  --name StripeServer \
  --base-url https://api.stripe.com \
  --output ./servers/stripe
```

### Generated Tools (subset)

```python
@mcp.tool()
def create_customer(email: str, name: str = None) -> dict:
    """Create a new Stripe customer.

    Args:
        email: Customer email
        name: Customer name

    Returns:
        Created customer object
    """
    api_key = require_auth("STRIPE_API_KEY")
    response = httpx.post(
        f"{BASE_URL}/v1/customers",
        auth=(api_key, ""),
        data={"email": email, "name": name}
    )
    response.raise_for_status()
    return response.json()

@mcp.tool()
def create_payment_intent(
    amount: int,
    currency: str = "usd",
    customer: str = None
) -> dict:
    """Create a payment intent.

    Args:
        amount: Amount in cents
        currency: Three-letter currency code
        customer: Customer ID

    Returns:
        Payment intent object with client_secret
    """
    api_key = require_auth("STRIPE_API_KEY")
    data = {"amount": amount, "currency": currency}
    if customer:
        data["customer"] = customer

    response = httpx.post(
        f"{BASE_URL}/v1/payment_intents",
        auth=(api_key, ""),
        data=data
    )
    response.raise_for_status()
    return response.json()
```

---

## Multi-Service Aggregator

Combine multiple APIs into one server.

### Generate

```bash
mcp-factory generate \
  "Multi-service aggregator:
   1. Weather tools (OpenWeatherMap API):
      - get_weather(city)
      - get_forecast(city, days)

   2. News tools (NewsAPI):
      - get_headlines(country, category)
      - search_news(query)

   3. Stock tools (Alpha Vantage):
      - get_stock_price(symbol)
      - get_stock_history(symbol, days)

   Each service uses its own API key." \
  --name MultiServiceServer \
  --auth WEATHER_API_KEY \
  --auth NEWS_API_KEY \
  --auth ALPHAVANTAGE_API_KEY \
  --web-search \
  --output ./servers/multi-service
```

### Generated Server Structure

```python
from mcp.server.fastmcp import FastMCP
import httpx
import os

mcp = FastMCP("MultiServiceServer")

# Multiple API configurations
AUTH_CONFIG = {
    "WEATHER_API_KEY": os.environ.get("WEATHER_API_KEY"),
    "NEWS_API_KEY": os.environ.get("NEWS_API_KEY"),
    "ALPHAVANTAGE_API_KEY": os.environ.get("ALPHAVANTAGE_API_KEY"),
}

API_URLS = {
    "weather": "https://api.openweathermap.org/data/2.5",
    "news": "https://newsapi.org/v2",
    "stocks": "https://www.alphavantage.co/query",
}

# Weather tools
@mcp.tool()
def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    api_key = require_auth("WEATHER_API_KEY")
    # Implementation...

@mcp.tool()
def get_forecast(city: str, days: int = 5) -> dict:
    """Get weather forecast."""
    api_key = require_auth("WEATHER_API_KEY")
    # Implementation...

# News tools
@mcp.tool()
def get_headlines(country: str = "us", category: str = "general") -> dict:
    """Get top news headlines."""
    api_key = require_auth("NEWS_API_KEY")
    # Implementation...

@mcp.tool()
def search_news(query: str, page_size: int = 10) -> dict:
    """Search news articles."""
    api_key = require_auth("NEWS_API_KEY")
    # Implementation...

# Stock tools
@mcp.tool()
def get_stock_price(symbol: str) -> dict:
    """Get current stock price."""
    api_key = require_auth("ALPHAVANTAGE_API_KEY")
    # Implementation...

@mcp.tool()
def get_stock_history(symbol: str, days: int = 30) -> dict:
    """Get historical stock prices."""
    api_key = require_auth("ALPHAVANTAGE_API_KEY")
    # Implementation...
```

---

## Production Server

Full production-ready server with all features enabled.

### Generate

```bash
mcp-factory generate \
  "Production API server with:
   - User management (create, read, update, delete)
   - Rate limiting (100 requests/minute)
   - Structured logging
   - Prometheus metrics
   - Health check endpoint" \
  --name ProductionServer \
  --auth API_KEY \
  --enable-logging \
  --enable-metrics \
  --enable-rate-limiting \
  --rate-limit 100 \
  --rate-window 60 \
  --output ./servers/production
```

### Python API

```python
import asyncio
from tool_factory import ToolFactoryAgent
from tool_factory.config import FactoryConfig, LLMProvider
from tool_factory.production import ProductionConfig

async def main():
    # Configure agent
    config = FactoryConfig(
        provider=LLMProvider.ANTHROPIC,
        model="claude-sonnet-4-5-20241022",
    )

    # Configure production features
    prod_config = ProductionConfig(
        enable_logging=True,
        enable_metrics=True,
        enable_rate_limiting=True,
        rate_limit_requests=100,
        rate_limit_window_seconds=60,
        enable_retries=True,
        max_retries=3,
    )

    agent = ToolFactoryAgent(config=config)

    result = await agent.generate_from_description(
        description="""
        Production-ready user management API:
        - create_user(email, name) - Create new user
        - get_user(user_id) - Get user by ID
        - update_user(user_id, name, email) - Update user
        - delete_user(user_id) - Delete user
        - list_users(limit, offset) - List users with pagination
        - health_check() - Server health status
        """,
        server_name="ProductionServer",
        auth_env_vars=["API_KEY"],
        include_health_check=True,
        production_config=prod_config,
    )

    # Write to disk
    result.write_to_directory("./servers/production")

    print(f"Generated {len(result.tool_specs)} tools")
    print("Files created:")
    print("  - server.py")
    print("  - tests/test_tools.py")
    print("  - Dockerfile")
    print("  - docker-compose.yml")
    print("  - pyproject.toml")
    print("  - README.md")
    print("  - .github/workflows/ci.yml")

asyncio.run(main())
```

### Generated Files

```
production/
├── server.py              # Full server with production features
├── tests/
│   └── test_tools.py      # Comprehensive tests
├── Dockerfile             # Production Dockerfile
├── docker-compose.yml     # With Prometheus & Grafana
├── prometheus.yml         # Prometheus configuration
├── pyproject.toml         # Python package config
├── requirements.txt       # Dependencies
├── README.md              # Setup documentation
├── skill.md               # Claude Code skill file
├── .github/
│   └── workflows/
│       └── ci.yml         # CI/CD pipeline
├── EXECUTION_LOG.md       # Generation trace
└── execution_log.json     # Machine-readable trace
```

### Deploy

```bash
cd ./servers/production

# Local
export API_KEY=your-key
python server.py

# Docker
docker build -t production-server .
docker run -e API_KEY=your-key -p 8000:8000 production-server

# Docker Compose (with monitoring)
API_KEY=your-key docker-compose up
```

---

## Running Examples

### Clone and Run

```bash
# Clone repository
git clone https://github.com/your-org/mcp-tool-factory
cd mcp-tool-factory/examples

# Install
pip install mcp-tool-factory[anthropic]

# Set API key
export ANTHROPIC_API_KEY=your-key

# Generate weather server
mcp-factory generate "Weather API" --output ./weather

# Run
cd weather
export WEATHER_API_KEY=your-weather-key
python server.py
```

### Test with MCP Inspector

```bash
# Install inspector
npm install -g @anthropic/mcp-inspector

# Run inspector with your server
mcp-inspector python ./server.py
```

### Configure in Claude Desktop

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["/path/to/weather/server.py"],
      "env": {
        "WEATHER_API_KEY": "your-key"
      }
    }
  }
}
```

---

## Next Steps

- [Getting Started](./getting-started.md) - Installation guide
- [CLI Reference](./cli-reference.md) - Full command reference
- [Production Features](./production.md) - Enable monitoring
- [Security](./security.md) - Security best practices
