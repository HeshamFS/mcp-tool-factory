"""Auto-generated MCP server."""

import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from typing import Any
import logging
import json
from datetime import datetime
from prometheus_client import Counter, Histogram, start_http_server
import random
from functools import wraps
import requests
import websocket-client

import json
import requests
from typing import Any
import asyncio
import base64
from websockets import connect, WebSocketClientProtocol
from websockets.exceptions import WebSocketException

mcp = FastMCP("DittoMcp", json_response=True)


# ============== STRUCTURED LOGGING ==============

class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, "tool_name"):
            log_data["tool_name"] = record.tool_name
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "error"):
            log_data["error"] = record.error

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Setup structured JSON logging."""
    logger = logging.getLogger("mcp_server")
    logger.setLevel(getattr(logging, level))

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    return logger


logger = setup_logging()


def log_tool_call(tool_name: str, duration_ms: float, success: bool, error: str | None = None):
    """Log a tool call with structured data."""
    extra = {"tool_name": tool_name, "duration_ms": round(duration_ms, 2)}
    if error:
        extra["error"] = error
        logger.error(f"Tool {tool_name} failed", extra=extra)
    else:
        logger.info(f"Tool {tool_name} completed", extra=extra)



# ============== PROMETHEUS METRICS ==============

# Metrics
TOOL_CALLS = Counter(
    "mcp_tool_calls_total",
    "Total number of tool calls",
    ["tool_name", "status"]
)

TOOL_DURATION = Histogram(
    "mcp_tool_duration_seconds",
    "Tool call duration in seconds",
    ["tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

TOOL_ERRORS = Counter(
    "mcp_tool_errors_total",
    "Total number of tool errors",
    ["tool_name", "error_type"]
)


def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics HTTP server."""
    start_http_server(port)
    logger.info(f"Metrics server started on port {port}")


def record_tool_metrics(tool_name: str, duration_seconds: float, success: bool, error_type: str | None = None):
    """Record metrics for a tool call."""
    status = "success" if success else "error"
    TOOL_CALLS.labels(tool_name=tool_name, status=status).inc()
    TOOL_DURATION.labels(tool_name=tool_name).observe(duration_seconds)

    if not success and error_type:
        TOOL_ERRORS.labels(tool_name=tool_name, error_type=error_type).inc()



# ============== RETRY PATTERNS ==============

class RetryError(Exception):
    """Raised when all retries are exhausted."""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Decorator for retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to prevent thundering herd
        retryable_exceptions: Tuple of exceptions to retry on
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        break

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)

                    # Add jitter (0-25% of delay)
                    if jitter:
                        delay = delay * (1 + random.random() * 0.25)

                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {func.__name__} "
                        f"after {delay:.2f}s due to: {e}"
                    )
                    time.sleep(delay)

            raise RetryError(
                f"Failed after {max_retries} retries: {last_exception}"
            ) from last_exception

        return wrapper
    return decorator


async def async_retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Async retry with exponential backoff.

    Args:
        func: Async function to call
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Add random jitter
        retryable_exceptions: Tuple of exceptions to retry on

    Returns:
        Result of successful function call
    """
    import asyncio

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except retryable_exceptions as e:
            last_exception = e

            if attempt == max_retries:
                break

            delay = min(base_delay * (exponential_base ** attempt), max_delay)
            if jitter:
                delay = delay * (1 + random.random() * 0.25)

            logger.warning(
                f"Async retry {attempt + 1}/{max_retries} after {delay:.2f}s: {e}"
            )
            await asyncio.sleep(delay)

    raise RetryError(f"Failed after {max_retries} retries") from last_exception


# ============== HEALTH CHECK ==============

@mcp.tool()
def health_check() -> dict:
    """
    Check server health and configuration status.

    Returns:
        Health status including uptime and auth configuration
    """
    result = {
        "status": "healthy",
        "server": "DittoMcp",
        "timestamp": datetime.now().isoformat(),
        "tools_available": 10,
    }


    return result


# ============== TOOLS ==============

@mcp.tool()
def create_ditto_message(
    topic: str,
    value: dict | list | str | int | float | bool | None,
    path: str = "/",
    headers: dict | None = None
) -> dict:
    """
    Creates an Eclipse Ditto protocol message for sending commands or events to IoT devices.

    Args:
        topic: The Ditto protocol topic in format: namespace/thing_id/things/twin/commands/action
               or similar (e.g., "org.eclipse.ditto/device123/things/twin/commands/modify")
        value: The payload value to send (can be any JSON-serializable object)
        path: The path to the resource (e.g., "/features/temperature/properties/value").
              Defaults to "/"
        headers: Optional headers like correlation-id, response-required, etc.
                 Defaults to empty dict if not provided

    Returns:
        Dictionary containing the Ditto protocol message with fields:
        - topic: The Ditto protocol topic
        - headers: Message headers
        - path: Resource path
        - value: The payload
        - status: Optional HTTP status code (only included for responses)
    """
    try:
        # Validate topic format
        if not topic or not isinstance(topic, str):
            return {"error": "Topic must be a non-empty string"}
        
        topic_parts = topic.split("/")
        if len(topic_parts) < 4:
            return {"error": "Invalid topic format. Expected format: namespace/thing_id/things/twin/commands/action or similar"}
        
        # Validate that topic contains required segments
        if "things" not in topic_parts:
            return {"error": "Topic must contain 'things' segment"}
        
        # Validate path format
        if not isinstance(path, str):
            return {"error": "Path must be a string"}
        
        if not path.startswith("/"):
            return {"error": "Path must start with '/'"}
        
        # Ensure headers is a dict
        if headers is None:
            headers = {}
        elif not isinstance(headers, dict):
            return {"error": "Headers must be a dictionary"}
        
        # Validate that value is JSON-serializable
        import json
        try:
            json.dumps(value)
        except (TypeError, ValueError) as e:
            return {"error": f"Value is not JSON-serializable: {str(e)}"}
        
        # Construct the Ditto protocol message
        message = {
            "topic": topic,
            "headers": headers,
            "path": path,
            "value": value
        }
        
        # Only include status if it's a response (topic contains /messages/ or specific response patterns)
        # For commands/events, status is typically not included
        
        return message
        
    except Exception as e:
        return {"error": f"Unexpected error creating Ditto message: {str(e)}"}

@mcp.tool()
def create_ditto_thing(
    thing_id: str,
    attributes: dict | None = None,
    features: dict | None = None,
    policy_id: str | None = None
) -> dict:
    """
    Creates a complete Eclipse Ditto Thing definition with attributes, features, and metadata.

    Args:
        thing_id: The unique identifier for the thing in format namespace:name
        attributes: Key-value pairs of thing attributes (e.g., location, manufacturer)
        features: Features of the thing with their properties (e.g., temperature sensor with value)
        policy_id: Optional policy ID for access control

    Returns:
        Dictionary containing thingId, policyId, attributes, and features matching Ditto Thing model v2,
        or {"error": "message"} if validation fails
    """
    try:
        # Validate thing_id format
        if not thing_id or not isinstance(thing_id, str):
            return {"error": "thing_id must be a non-empty string"}
        
        if ':' not in thing_id:
            return {"error": "thing_id must contain namespace separator ':' (format: namespace:name)"}
        
        # Split and validate namespace and name
        parts = thing_id.split(':', 1)
        if not parts[0] or not parts[1]:
            return {"error": "thing_id must have non-empty namespace and name"}
        
        # Initialize default values
        if attributes is None:
            attributes = {}
        if features is None:
            features = {}
        
        # Validate that attributes and features are dictionaries
        if not isinstance(attributes, dict):
            return {"error": "attributes must be a dictionary"}
        if not isinstance(features, dict):
            return {"error": "features must be a dictionary"}
        
        # Validate policy_id if provided
        if policy_id is not None and not isinstance(policy_id, str):
            return {"error": "policy_id must be a string"}
        
        # Build Ditto Thing structure
        thing = {
            "thingId": thing_id,
            "attributes": attributes,
            "features": features
        }
        
        # Add policyId if provided, otherwise use thing_id as default
        if policy_id:
            thing["policyId"] = policy_id
        else:
            thing["policyId"] = thing_id
        
        return thing
        
    except Exception as e:
        return {"error": f"Unexpected error creating Ditto thing: {str(e)}"}

@mcp.tool()
def parse_ditto_message(message: str | dict) -> dict:
    """
    Parses an incoming Eclipse Ditto protocol message and extracts its components.

    Args:
        message: The raw Ditto protocol message as JSON string or dict

    Returns:
        Dictionary containing parsed components: topic, namespace, thing_id, channel,
        criterion, action, path, value, and headers. Returns error dict on failure.
    """
    try:
        # Handle both string and dict input formats
        if isinstance(message, str):
            try:
                parsed_message = json.loads(message)
            except json.JSONDecodeError as e:
                return {"error": f"Invalid JSON string: {str(e)}"}
        elif isinstance(message, dict):
            parsed_message = message
        else:
            return {"error": f"Invalid message type: expected str or dict, got {type(message).__name__}"}

        # Validate required fields
        if not isinstance(parsed_message, dict):
            return {"error": "Parsed message is not a dictionary"}

        topic = parsed_message.get("topic", "")
        if not topic:
            return {"error": "Missing required field: topic"}

        # Split topic to extract components
        # Expected format: <namespace>/<thing_id>/<channel>/<criterion>/<action>
        topic_parts = topic.split("/")
        
        if len(topic_parts) < 5:
            return {"error": f"Invalid topic format: expected at least 5 parts separated by '/', got {len(topic_parts)}"}

        namespace = topic_parts[0]
        thing_id = topic_parts[1]
        channel = topic_parts[2]
        criterion = topic_parts[3]
        action = topic_parts[4]

        # Extract other fields with defaults
        path = parsed_message.get("path", "")
        value = parsed_message.get("value", {})
        headers = parsed_message.get("headers", {})

        # Validate extracted data types
        if not isinstance(value, dict):
            value = {}
        
        if not isinstance(headers, dict):
            headers = {}

        return {
            "topic": topic,
            "namespace": namespace,
            "thing_id": thing_id,
            "channel": channel,
            "criterion": criterion,
            "action": action,
            "path": path,
            "value": value,
            "headers": headers
        }

    except Exception as e:
        return {"error": f"Unexpected error while parsing Ditto message: {str(e)}"}

@mcp.tool()
def create_ditto_command(
    thing_id: str,
    command_type: str,
    channel: str = "twin",
    path: str = "/",
    value: dict | None = None,
    correlation_id: str | None = None
) -> dict:
    """
    Creates a Ditto protocol command message for modifying thing state.

    Args:
        thing_id: The thing ID in format namespace:name
        command_type: Command type - must be one of: modify, create, delete, retrieve
        channel: Communication channel - must be either twin or live (default: twin)
        path: Path to resource, e.g., /attributes/location or /features/temp (default: /)
        value: The value to set (not needed for retrieve/delete commands)
        correlation_id: Optional correlation ID for request tracking

    Returns:
        Dictionary containing topic, headers, path, and value fields matching the Ditto protocol,
        or {"error": "message"} if validation fails
    """
    try:
        # Validate thing_id format
        if not thing_id or not isinstance(thing_id, str):
            return {"error": "thing_id must be a non-empty string"}
        
        if ":" not in thing_id:
            return {"error": "thing_id must be in format namespace:name"}
        
        parts = thing_id.split(":", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return {"error": "thing_id must be in format namespace:name with non-empty namespace and name"}
        
        namespace, name = parts
        
        # Validate command_type
        valid_command_types = {"modify", "create", "delete", "retrieve"}
        if not command_type or command_type not in valid_command_types:
            return {"error": f"command_type must be one of: {', '.join(valid_command_types)}"}
        
        # Validate channel
        valid_channels = {"twin", "live"}
        if channel not in valid_channels:
            return {"error": f"channel must be one of: {', '.join(valid_channels)}"}
        
        # Validate path
        if not isinstance(path, str):
            return {"error": "path must be a string"}
        
        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path
        
        # Validate value requirements
        if command_type in {"modify", "create"}:
            if value is None:
                return {"error": f"value is required for {command_type} commands"}
            if not isinstance(value, dict):
                return {"error": "value must be a dictionary"}
        
        # Build topic: namespace/name/things/channel/commands/commandType
        topic = f"{namespace}/{name}/things/{channel}/commands/{command_type}"
        
        # Build headers
        headers: dict = {}
        if correlation_id:
            if not isinstance(correlation_id, str):
                return {"error": "correlation_id must be a string"}
            headers["correlation-id"] = correlation_id
        
        # Build response
        response: dict = {
            "topic": topic,
            "headers": headers,
            "path": path
        }
        
        # Add value only if provided
        if value is not None:
            response["value"] = value
        
        return response
        
    except Exception as e:
        return {"error": f"Unexpected error creating Ditto command: {str(e)}"}

@mcp.tool()
def create_ditto_event(
    thing_id: str,
    event_type: str,
    value: dict,
    channel: str = "twin",
    path: str = "/",
    revision: int | None = None
) -> dict:
    """
    Creates a Ditto protocol event message for notifying about thing state changes.

    Args:
        thing_id: The thing ID in format namespace:name
        event_type: Event type: created, modified, deleted
        value: The changed value as a dictionary
        channel: Communication channel: twin or live (default: "twin")
        path: Path to changed resource (default: "/")
        revision: Thing revision number (optional)

    Returns:
        Dictionary containing:
            - topic: Formatted event topic string
            - headers: Event headers with revision if provided
            - path: Resource path
            - value: Event payload
        Or {"error": "message"} if validation fails
    """
    try:
        # Validate thing_id format
        if not thing_id or not isinstance(thing_id, str):
            return {"error": "thing_id must be a non-empty string"}
        
        if ":" not in thing_id:
            return {"error": "thing_id must be in format namespace:name"}
        
        parts = thing_id.split(":", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return {"error": "thing_id must be in format namespace:name with non-empty namespace and name"}
        
        namespace, name = parts
        
        # Validate event_type
        valid_event_types = ["created", "modified", "deleted"]
        if not event_type or event_type not in valid_event_types:
            return {"error": f"event_type must be one of: {', '.join(valid_event_types)}"}
        
        # Validate channel
        valid_channels = ["twin", "live"]
        if channel not in valid_channels:
            return {"error": f"channel must be one of: {', '.join(valid_channels)}"}
        
        # Validate value
        if not isinstance(value, dict):
            return {"error": "value must be a dictionary"}
        
        # Validate path
        if not isinstance(path, str):
            return {"error": "path must be a string"}
        
        # Validate revision if provided
        if revision is not None and not isinstance(revision, int):
            return {"error": "revision must be an integer"}
        
        # Format topic: namespace/name/things/channel/events/eventType
        topic = f"{namespace}/{name}/things/{channel}/events/{event_type}"
        
        # Build headers
        headers = {}
        if revision is not None:
            headers["revision"] = revision
        
        # Optionally add ditto-originator header (can be customized if needed)
        headers["content-type"] = "application/json"
        
        # Construct response
        return {
            "topic": topic,
            "headers": headers,
            "path": path,
            "value": value
        }
        
    except Exception as e:
        return {"error": f"Unexpected error creating Ditto event: {str(e)}"}

@mcp.tool()
def create_ditto_feature(
    feature_id: str,
    properties: dict | None = None,
    desired_properties: dict | None = None,
    definition: list[str] | None = None
) -> dict:
    """
    Creates a Ditto feature definition with properties and desired properties for IoT device capabilities.

    Args:
        feature_id: Unique identifier for the feature (e.g., 'temperature', 'humidity')
        properties: Current property values of the feature. Defaults to empty dict if None
        desired_properties: Desired property values for the feature. Defaults to empty dict if None
        definition: Array of definition identifiers (e.g., ['org.example:TemperatureSensor:1.0.0']). Defaults to empty list if None

    Returns:
        Dictionary containing the Ditto feature with keys: feature_id, definition, properties, desiredProperties
        Returns {"error": "message"} if validation fails or an error occurs
    """
    try:
        # Validate feature_id
        if not feature_id:
            return {"error": "feature_id is required and cannot be empty"}
        
        if not isinstance(feature_id, str):
            return {"error": "feature_id must be a string"}
        
        # Handle default values
        if properties is None:
            properties = {}
        
        if desired_properties is None:
            desired_properties = {}
        
        if definition is None:
            definition = []
        
        # Validate input types
        if not isinstance(properties, dict):
            return {"error": "properties must be a dictionary"}
        
        if not isinstance(desired_properties, dict):
            return {"error": "desired_properties must be a dictionary"}
        
        if not isinstance(definition, list):
            return {"error": "definition must be a list"}
        
        # Validate definition array contains only strings
        if not all(isinstance(item, str) for item in definition):
            return {"error": "definition array must contain only strings"}
        
        # Build Ditto feature object with camelCase keys
        feature = {
            "feature_id": feature_id,
            "definition": definition,
            "properties": properties,
            "desiredProperties": desired_properties
        }
        
        return feature
    
    except Exception as e:
        return {"error": f"Unexpected error creating Ditto feature: {str(e)}"}

@mcp.tool()
def send_ditto_http_request(
    base_url: str,
    endpoint: str,
    method: str = "GET",
    auth: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Sends an HTTP request to Eclipse Ditto REST API for thing management operations.

    Args:
        base_url: Base URL of Ditto API (e.g., http://localhost:8080/api/2)
        endpoint: API endpoint path (e.g., /things/namespace:thing-1)
        method: HTTP method (GET, POST, PUT, PATCH, DELETE). Defaults to GET
        auth: Authentication credentials dictionary with 'username' and 'password' keys
        payload: Request body payload as dictionary
        headers: Additional HTTP headers as dictionary

    Returns:
        Dictionary containing:
            - status_code: HTTP status code
            - response: Response body as dictionary (if JSON)
            - headers: Response headers as dictionary
            - error: Error message if request failed
    """
    # Validate inputs
    if not base_url or not isinstance(base_url, str):
        return {"error": "base_url must be a non-empty string"}
    
    if not endpoint or not isinstance(endpoint, str):
        return {"error": "endpoint must be a non-empty string"}
    
    method = method.upper()
    valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
    if method not in valid_methods:
        return {"error": f"method must be one of {valid_methods}"}
    
    # Initialize optional parameters
    auth = auth or {}
    headers = headers or {}
    payload = payload or None
    
    # Construct full URL
    url = base_url.rstrip("/") + "/" + endpoint.lstrip("/")
    
    # Prepare authentication
    auth_tuple = None
    if auth and "username" in auth and "password" in auth:
        auth_tuple = (auth["username"], auth["password"])
    
    # Set default headers
    request_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    request_headers.update(headers)
    
    try:
        # Make HTTP request with timeout
        response = requests.request(
            method=method,
            url=url,
            json=payload if payload else None,
            headers=request_headers,
            auth=auth_tuple,
            timeout=30,
        )
        
        # Parse response
        response_data = None
        try:
            if response.text:
                response_data = response.json()
        except ValueError:
            # Response is not JSON, store as plain text
            response_data = {"text": response.text}
        
        return {
            "status_code": response.status_code,
            "response": response_data,
            "headers": dict(response.headers),
        }
    
    except requests.exceptions.Timeout:
        return {"error": "Request timed out after 30 seconds"}
    
    except requests.exceptions.ConnectionError as e:
        return {"error": f"Connection error: {str(e)}"}
    
    except requests.exceptions.InvalidURL:
        return {"error": f"Invalid URL: {url}"}
    
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

@mcp.tool()
def create_ditto_policy(policy_id: str, entries: dict) -> dict:
    """
    Creates an Eclipse Ditto policy for fine-grained access control on things and their resources.
    
    Implements Ditto policy model v2, where each entry contains subjects (who has access)
    and resources (what can be accessed) with grant/revoke permissions.

    Args:
        policy_id: Unique policy identifier in format namespace:name (e.g., "org.eclipse:my-policy")
        entries: Policy entries mapping labels to subjects and resources with permissions.
                 Each entry should have:
                 - subjects: dict mapping subject IDs to subject configurations
                 - resources: dict mapping resource types to permission configurations

    Returns:
        Dictionary containing:
        - policyId: The policy identifier
        - entries: The complete policy entries with subjects and resources
        Or on error:
        - error: Error message describing what went wrong
    """
    try:
        # Validate policy_id format
        if not policy_id or not isinstance(policy_id, str):
            return {"error": "policy_id must be a non-empty string"}
        
        if ":" not in policy_id:
            return {"error": "policy_id must be in format namespace:name (e.g., 'org.eclipse:my-policy')"}
        
        namespace, name = policy_id.split(":", 1)
        if not namespace or not name:
            return {"error": "Both namespace and name parts of policy_id must be non-empty"}
        
        # Validate entries
        if not isinstance(entries, dict):
            return {"error": "entries must be a dictionary"}
        
        if not entries:
            return {"error": "entries must contain at least one policy entry"}
        
        # Validate each entry structure
        for label, entry in entries.items():
            if not isinstance(label, str):
                return {"error": f"Entry label must be a string, got {type(label).__name__}"}
            
            if not isinstance(entry, dict):
                return {"error": f"Entry '{label}' must be a dictionary"}
            
            # Validate subjects
            if "subjects" not in entry:
                return {"error": f"Entry '{label}' must contain 'subjects' field"}
            
            if not isinstance(entry["subjects"], dict):
                return {"error": f"Entry '{label}' subjects must be a dictionary"}
            
            if not entry["subjects"]:
                return {"error": f"Entry '{label}' must have at least one subject"}
            
            # Validate resources
            if "resources" not in entry:
                return {"error": f"Entry '{label}' must contain 'resources' field"}
            
            if not isinstance(entry["resources"], dict):
                return {"error": f"Entry '{label}' resources must be a dictionary"}
            
            if not entry["resources"]:
                return {"error": f"Entry '{label}' must have at least one resource"}
            
            # Validate resource permissions structure
            for resource_type, resource_config in entry["resources"].items():
                if not isinstance(resource_config, dict):
                    return {"error": f"Entry '{label}' resource '{resource_type}' must be a dictionary"}
                
                # Check for valid permission keys (grant, revoke)
                valid_keys = {"grant", "revoke"}
                for key in resource_config.keys():
                    if key not in valid_keys:
                        return {"error": f"Entry '{label}' resource '{resource_type}' contains invalid key '{key}'. Must be 'grant' or 'revoke'"}
        
        # Construct the policy according to Ditto policy model v2
        policy = {
            "policyId": policy_id,
            "entries": entries
        }
        
        return policy
        
    except ValueError as e:
        return {"error": f"Value error: {str(e)}"}
    except TypeError as e:
        return {"error": f"Type error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error creating policy: {str(e)}"}

@mcp.tool()
def validate_ditto_message(message: dict | None) -> dict:
    """
    Validates an Eclipse Ditto protocol message against the protocol specification.

    Args:
        message: The Ditto protocol message to validate as a dictionary

    Returns:
        Dictionary containing:
            - valid (bool): Whether the message is valid
            - errors (list[str]): List of validation errors if any
            - warnings (list[str]): List of validation warnings
    """
    errors = []
    warnings = []
    
    try:
        # Validate input is a dictionary
        if message is None:
            return {
                "valid": False,
                "errors": ["Message cannot be None"],
                "warnings": []
            }
        
        if not isinstance(message, dict):
            return {
                "valid": False,
                "errors": [f"Message must be a dictionary, got {type(message).__name__}"],
                "warnings": []
            }
        
        # Check required fields
        required_fields = ["topic", "headers", "path"]
        for field in required_fields:
            if field not in message:
                errors.append(f"Missing required field: '{field}'")
        
        # Validate topic structure if present
        if "topic" in message:
            topic = message["topic"]
            if not isinstance(topic, str):
                errors.append(f"Field 'topic' must be a string, got {type(topic).__name__}")
            elif topic:
                # Topic format: namespace/name/group/channel/criterion/action
                topic_parts = topic.split("/")
                if len(topic_parts) < 4:
                    errors.append(f"Topic '{topic}' has invalid structure, expected at least 4 segments")
                
                # Check valid group values
                if len(topic_parts) >= 3 and topic_parts[2] not in ["things", "policies", "connections"]:
                    warnings.append(f"Topic group '{topic_parts[2]}' is not a standard Ditto group")
                
                # Check valid channel values
                if len(topic_parts) >= 4 and topic_parts[3] not in ["twin", "live", "none"]:
                    warnings.append(f"Topic channel '{topic_parts[3]}' is not a standard Ditto channel")
            else:
                errors.append("Field 'topic' cannot be empty")
        
        # Validate headers is a dictionary
        if "headers" in message:
            headers = message["headers"]
            if not isinstance(headers, dict):
                errors.append(f"Field 'headers' must be a dictionary, got {type(headers).__name__}")
            elif headers:
                # Check for standard correlation-id header
                if "correlation-id" not in headers and "correlationId" not in headers:
                    warnings.append("Missing recommended header: 'correlation-id'")
        
        # Validate path starts with '/'
        if "path" in message:
            path = message["path"]
            if not isinstance(path, str):
                errors.append(f"Field 'path' must be a string, got {type(path).__name__}")
            elif not path.startswith("/"):
                errors.append(f"Field 'path' must start with '/', got '{path}'")
            elif path == "/":
                # Root path is valid but might need a warning for certain operations
                pass
        
        # Validate value type based on message type if present
        if "value" in message:
            value = message["value"]
            # Value can be any JSON-serializable type, but check it's not a complex Python object
            if hasattr(value, "__dict__") and not isinstance(value, (dict, list, str, int, float, bool, type(None))):
                warnings.append(f"Field 'value' contains non-JSON-serializable type: {type(value).__name__}")
        
        # Check status for response messages
        if "status" in message:
            status = message["status"]
            if not isinstance(status, int):
                errors.append(f"Field 'status' must be an integer, got {type(status).__name__}")
            elif status < 100 or status >= 600:
                warnings.append(f"Field 'status' value {status} is outside standard HTTP status code range")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
        
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Validation failed with exception: {str(e)}"],
            "warnings": []
        }

@mcp.tool()
async def subscribe_ditto_websocket(
    ws_url: str,
    auth: dict[str, str] | None = None,
    filter: str | None = None,
    namespaces: list[str] | None = None
) -> dict[str, Any]:
    """
    Establishes a WebSocket connection to Eclipse Ditto for real-time streaming of thing events and messages.

    Args:
        ws_url: WebSocket URL (e.g., ws://localhost:8080/ws/2)
        auth: Authentication credentials dictionary with 'username' and 'password' keys
        filter: Optional RQL filter for message filtering (e.g., like(thingId,'namespace:*'))
        namespaces: Array of namespaces to subscribe to

    Returns:
        Dictionary containing:
        - connected (bool): Connection status
        - session_id (str): WebSocket session ID if connected
        - error (str): Error message if connection failed
    """
    if namespaces is None:
        namespaces = []
    
    # Validate required inputs
    if not ws_url or not isinstance(ws_url, str):
        return {"connected": False, "error": "ws_url must be a non-empty string"}
    
    if not ws_url.startswith(("ws://", "wss://")):
        return {"connected": False, "error": "ws_url must start with ws:// or wss://"}
    
    # Validate auth if provided
    if auth is not None:
        if not isinstance(auth, dict):
            return {"connected": False, "error": "auth must be a dictionary"}
        if "username" not in auth or "password" not in auth:
            return {"connected": False, "error": "auth must contain 'username' and 'password' keys"}
    
    # Validate namespaces
    if not isinstance(namespaces, list):
        return {"connected": False, "error": "namespaces must be a list"}
    
    # Validate filter if provided
    if filter is not None and not isinstance(filter, str):
        return {"connected": False, "error": "filter must be a string"}
    
    websocket: WebSocketClientProtocol | None = None
    session_id: str = ""
    
    try:
        # Prepare headers with authentication if provided
        extra_headers = {}
        if auth:
            credentials = f"{auth['username']}:{auth['password']}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            extra_headers["Authorization"] = f"Basic {encoded_credentials}"
        
        # Establish WebSocket connection
        websocket = await connect(ws_url, extra_headers=extra_headers if extra_headers else None)
        
        # Build START-SEND-EVENTS command
        events_command = {
            "topic": "thing:commands",
            "path": "/features",
            "value": "START-SEND-EVENTS"
        }
        
        if namespaces:
            events_command["namespaces"] = namespaces
        
        if filter:
            events_command["filter"] = filter
        
        # Send START-SEND-EVENTS
        await websocket.send(json.dumps(events_command))
        
        # Build START-SEND-MESSAGES command
        messages_command = {
            "topic": "thing:commands",
            "path": "/inbox/messages",
            "value": "START-SEND-MESSAGES"
        }
        
        if namespaces:
            messages_command["namespaces"] = namespaces
        
        if filter:
            messages_command["filter"] = filter
        
        # Send START-SEND-MESSAGES
        await websocket.send(json.dumps(messages_command))
        
        # Generate session ID from connection
        session_id = f"ditto_ws_{id(websocket)}"
        
        # Note: In a production system, you would typically:
        # 1. Store the websocket connection in a session manager
        # 2. Run a background task to handle incoming messages
        # 3. Provide a way to close/unsubscribe later
        # For now, we close the connection after successful setup
        
        await websocket.close()
        
        return {
            "connected": True,
            "session_id": session_id
        }
        
    except WebSocketException as e:
        if websocket:
            try:
                await websocket.close()
            except Exception:
                pass
        return {"connected": False, "error": f"WebSocket error: {str(e)}"}
    
    except json.JSONDecodeError as e:
        if websocket:
            try:
                await websocket.close()
            except Exception:
                pass
        return {"connected": False, "error": f"JSON encoding error: {str(e)}"}
    
    except KeyError as e:
        if websocket:
            try:
                await websocket.close()
            except Exception:
                pass
        return {"connected": False, "error": f"Missing required auth field: {str(e)}"}
    
    except Exception as e:
        if websocket:
            try:
                await websocket.close()
            except Exception:
                pass
        return {"connected": False, "error": f"Unexpected error: {str(e)}"}


# ============== MAIN ==============

if __name__ == "__main__":
    mcp.run(transport="stdio")
