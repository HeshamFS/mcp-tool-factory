# Troubleshooting

Common issues and solutions when using MCP Tool Factory.

## Quick Diagnostics

```bash
# Check installation
mcp-factory info

# Verify provider configuration
mcp-factory info --verbose
```

---

## Installation Issues

### "Command not found: mcp-factory"

**Cause:** Package not installed or not in PATH.

**Solutions:**

```bash
# Install the package
pip install mcp-tool-factory

# Or install with pipx (recommended)
pipx install mcp-tool-factory

# Verify installation
which mcp-factory
mcp-factory --version
```

If using a virtual environment:

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate   # Windows

# Then install
pip install mcp-tool-factory
```

### "No module named 'anthropic'"

**Cause:** Provider extras not installed.

**Solution:**

```bash
# Install with Anthropic support
pip install mcp-tool-factory[anthropic]

# Or all providers
pip install mcp-tool-factory[all]
```

### "Python version not supported"

**Cause:** MCP Tool Factory requires Python 3.10+.

**Solution:**

```bash
# Check Python version
python --version

# Install Python 3.11+
# macOS
brew install python@3.11

# Ubuntu
sudo apt install python3.11

# Windows - download from python.org
```

---

## Provider Issues

### "ANTHROPIC_API_KEY not set"

**Cause:** API key environment variable not configured.

**Solutions:**

```bash
# Set temporarily
export ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Set permanently (add to ~/.bashrc or ~/.zshrc)
echo 'export ANTHROPIC_API_KEY=sk-ant-api03-xxxxx' >> ~/.bashrc
source ~/.bashrc

# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-api03-xxxxx"

# Windows Command Prompt
set ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

### "Invalid API key"

**Cause:** API key is malformed or expired.

**Solutions:**

1. Verify key format:
   - Anthropic: `sk-ant-api03-...`
   - OpenAI: `sk-...`
   - Google: alphanumeric string

2. Generate new key:
   - Anthropic: [console.anthropic.com](https://console.anthropic.com/)
   - OpenAI: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
   - Google: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### "Rate limit exceeded"

**Cause:** Too many API requests in a short period.

**Solutions:**

```bash
# Wait and retry
sleep 60
mcp-factory generate "My tools"

# Or use a different provider
mcp-factory generate "My tools" --provider openai
```

For programmatic usage:

```python
import time
from tool_factory import ToolFactoryAgent

agent = ToolFactoryAgent()

for description in descriptions:
    try:
        result = agent.generate_from_description_sync(description)
    except Exception as e:
        if "rate_limit" in str(e).lower():
            time.sleep(60)
            result = agent.generate_from_description_sync(description)
```

### "Model not found"

**Cause:** Invalid model name.

**Solution:** Use valid model names:

```bash
# Anthropic models
--model claude-sonnet-4-5-20241022
--model claude-opus-4-5-20251101
--model claude-haiku-4-5-20241022

# OpenAI models
--model gpt-5.2
--model gpt-4.1
--model o3

# Google models
--model gemini-2.0-flash
--model gemini-3-pro
```

---

## Generation Issues

### "Failed to parse LLM response"

**Cause:** LLM returned malformed JSON.

**Solutions:**

1. Retry the generation (LLM outputs vary):

```bash
mcp-factory generate "Weather API tools"
```

2. Simplify the description:

```bash
# Instead of complex description
mcp-factory generate "Create a weather API with current conditions, \
  forecasts, alerts, historical data, and location search"

# Use simpler description
mcp-factory generate "Weather API with current conditions and forecasts"
```

3. Use a more capable model:

```bash
mcp-factory generate "Complex API" --model claude-opus-4-5-20251101
```

### "Syntax error in generated code"

**Cause:** Generated Python code has errors.

**Solutions:**

1. Check the execution log:

```bash
cat ./output/EXECUTION_LOG.md
```

2. Run syntax check:

```bash
python -m py_compile ./output/server.py
```

3. Regenerate with different seed:

```bash
mcp-factory generate "My API" --output ./output-v2
```

### "No tools generated"

**Cause:** Description too vague or LLM didn't understand.

**Solutions:**

1. Be more specific:

```bash
# Instead of
mcp-factory generate "API tools"

# Use
mcp-factory generate "REST API tools for user management with create, \
  read, update, and delete operations"
```

2. Enable web search for API documentation:

```bash
mcp-factory generate "Stripe payment API" --web-search
```

### "Tool has no implementation"

**Cause:** LLM generated stub instead of implementation.

**Solutions:**

1. Add more context:

```bash
mcp-factory generate "Weather API using OpenWeatherMap REST API with \
  API key authentication, returning JSON with temperature and conditions"
```

2. Use web search:

```bash
mcp-factory generate "OpenWeatherMap API" --web-search
```

---

## OpenAPI Issues

### "OpenAPI spec validation failed"

**Cause:** Invalid or incomplete OpenAPI specification.

**Solutions:**

1. Validate the spec:

```bash
# Install validator
pip install openapi-spec-validator

# Validate
python -c "from openapi_spec_validator import validate; \
  import yaml; validate(yaml.safe_load(open('api.yaml')))"
```

2. Check required fields:

```yaml
# Required top-level fields
openapi: "3.0.0"  # or "3.1.0"
info:
  title: "My API"
  version: "1.0.0"
paths: {}  # At least empty object
```

3. Fix common issues:

```yaml
# Wrong
openapi: 3.0.0  # Must be string

# Correct
openapi: "3.0.0"
```

### "Base URL not found"

**Cause:** No `servers` section in spec.

**Solutions:**

1. Add servers to spec:

```yaml
servers:
  - url: https://api.example.com/v1
```

2. Or provide via CLI:

```bash
mcp-factory from-openapi ./api.yaml --base-url https://api.example.com
```

### "Authentication not detected"

**Cause:** Missing or malformed security schemes.

**Solution:** Add security configuration:

```yaml
components:
  securitySchemes:
    ApiKey:
      type: apiKey
      in: header
      name: X-API-Key

security:
  - ApiKey: []
```

---

## Database Issues

### "Could not connect to database"

**SQLite:**

```bash
# Check file exists
ls -la ./myapp.db

# Check permissions
chmod 644 ./myapp.db

# Test connection
sqlite3 ./myapp.db ".tables"
```

**PostgreSQL:**

```bash
# Test connection
psql "postgresql://user:pass@localhost/mydb" -c "SELECT 1"

# Check server is running
pg_isready -h localhost -p 5432

# Check network access
telnet localhost 5432
```

### "No tables found"

**Cause:** Database is empty or wrong schema.

**Solutions:**

```sql
-- PostgreSQL: List tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public';

-- SQLite: List tables
SELECT name FROM sqlite_master WHERE type='table';
```

```bash
# Specify schema for PostgreSQL
mcp-factory from-database "postgresql://...?options=-csearch_path=myschema"
```

### "Primary key not detected"

**Cause:** Table lacks PRIMARY KEY constraint.

**Solution:**

```sql
-- Add primary key
ALTER TABLE logs ADD COLUMN id SERIAL PRIMARY KEY;
```

Tables without primary keys only get `list` and `create` operations.

---

## Runtime Issues

### "Missing required auth"

**Cause:** Environment variable not set when running server.

**Solution:**

```bash
# Check required variables in health check
python server.py &
curl http://localhost:8000/health

# Set variables
export WEATHER_API_KEY=your-key
python server.py
```

### "Connection refused"

**Cause:** Server not running or wrong port.

**Solutions:**

```bash
# Check if server is running
ps aux | grep server.py

# Check port
lsof -i :8000

# Use different port
PORT=8080 python server.py
```

### "Rate limit exceeded" (runtime)

**Cause:** Server's rate limiting triggered.

**Solution:**

```bash
# Check current limits
curl http://localhost:8000/health | jq .rate_limit

# Increase limits in server.py
rate_limiter = RateLimiter(max_requests=1000, window_seconds=60)
```

### "Request timeout"

**Cause:** External API is slow.

**Solutions:**

```python
# Increase timeout
response = httpx.get(url, timeout=60.0)

# Or configure globally
client = httpx.Client(timeout=60.0)
```

---

## Docker Issues

### "Module not found" in container

**Cause:** Dependencies missing in Dockerfile.

**Solution:** Check generated requirements.txt:

```bash
# View dependencies
cat requirements.txt

# Add missing dependencies
echo "prometheus_client>=0.17.0" >> requirements.txt

# Rebuild
docker build -t my-server .
```

### "Health check failing"

**Cause:** Server not responding to health check.

**Solution:**

```bash
# Check container logs
docker logs my-server

# Check health endpoint
docker exec my-server curl http://localhost:8000/health
```

### "Cannot connect to server"

**Cause:** Port not exposed or wrong binding.

**Solution:**

```bash
# Expose port
docker run -p 8000:8000 my-server

# Bind to all interfaces in server.py
mcp.run(host="0.0.0.0", port=8000)
```

---

## Test Issues

### "Tests failing"

```bash
# Run with verbose output
mcp-factory test ./server.py --verbose

# Run specific test
pytest tests/test_tools.py -v

# Check test output
pytest tests/ --tb=long
```

### "Import error in tests"

**Cause:** Server not on Python path.

**Solution:**

```bash
# Add to path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install locally
pip install -e .
```

---

## Performance Issues

### "Generation is slow"

**Solutions:**

1. Use faster model:

```bash
mcp-factory generate "Simple tools" --model claude-haiku-4-5-20241022
```

2. Simplify description
3. Disable web search if not needed

### "Server response slow"

**Solutions:**

1. Add connection pooling:

```python
client = httpx.Client(limits=httpx.Limits(max_connections=100))
```

2. Add caching:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_data(key: str) -> dict:
    # ...
```

---

## Getting Help

### Collect Diagnostic Info

```bash
# Save to file
mcp-factory info --verbose > diagnostics.txt

# Include execution log
cat ./output/EXECUTION_LOG.md >> diagnostics.txt
cat ./output/execution_log.json >> diagnostics.txt
```

### Report Issues

1. Search existing issues: [GitHub Issues](https://github.com/anthropics/mcp-tool-factory/issues)
2. If not found, create new issue with:
   - MCP Tool Factory version
   - Python version
   - Provider used
   - Full error message
   - Minimal reproduction steps
   - Diagnostic info

### Community Resources

- [MCP Documentation](https://modelcontextprotocol.info/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [Claude Code Documentation](https://claude.ai/docs/code)

---

## Error Reference

| Error | Cause | Solution |
|-------|-------|----------|
| `ANTHROPIC_API_KEY not set` | Missing env var | Set `ANTHROPIC_API_KEY` |
| `Invalid API key` | Bad key format | Check key format, regenerate |
| `Rate limit exceeded` | Too many requests | Wait 60s, try again |
| `Model not found` | Invalid model name | Use valid model ID |
| `Failed to parse response` | LLM error | Retry, simplify description |
| `Syntax error` | Bad code gen | Regenerate, check log |
| `OpenAPI validation failed` | Bad spec | Validate spec, fix errors |
| `Base URL not found` | Missing servers | Add servers or `--base-url` |
| `Connection refused` | Server not running | Start server, check port |
| `Missing required auth` | Env var missing | Set required env vars |
