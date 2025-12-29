FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir mcp prometheus_client requests tenacity websocket-client

# Copy server code
COPY server.py .
# Health check - verifies server module loads correctly
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import server; print('OK')"

# Run the server
CMD ["python", "server.py"]
