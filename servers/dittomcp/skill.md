# DittoMcp

IoT device management tools for AI agents

## Overview

This MCP server provides 10 tools for AI agents.

## Available Tools

### create_ditto_message

Creates an Eclipse Ditto protocol message for sending commands or events to IoT devices.

**Parameters:**
- `topic` (required): The Ditto protocol topic in format: namespace/thing_id/things/twin/commands/action or similar
- `path` (optional): The path to the resource (e.g., /features/temperature/properties/value)
- `value` (required): The payload value to send (can be any JSON-serializable object)
- `headers` (optional): Optional headers like correlation-id, response-required, etc.

**Example:**
```
Use the create_ditto_message tool to creates an eclipse ditto protocol message for sending commands or events to iot devices.
```

### create_ditto_thing

Creates a complete Eclipse Ditto Thing definition with attributes, features, and metadata.

**Parameters:**
- `thing_id` (required): The unique identifier for the thing in format namespace:name
- `attributes` (optional): Key-value pairs of thing attributes (e.g., location, manufacturer)
- `features` (optional): Features of the thing with their properties (e.g., temperature sensor with value)
- `policy_id` (optional): Optional policy ID for access control

**Example:**
```
Use the create_ditto_thing tool to creates a complete eclipse ditto thing definition with attributes, features, and metadata.
```

### parse_ditto_message

Parses an incoming Eclipse Ditto protocol message and extracts its components.

**Parameters:**
- `message` (required): The raw Ditto protocol message as JSON string or dict

**Example:**
```
Use the parse_ditto_message tool to parses an incoming eclipse ditto protocol message and extracts its components.
```

### create_ditto_command

Creates a Ditto protocol command message for modifying thing state (modify, create, delete, retrieve).

**Parameters:**
- `thing_id` (required): The thing ID in format namespace:name
- `command_type` (required): Command type: modify, create, delete, or retrieve
- `channel` (optional): Communication channel: twin or live
- `path` (optional): Path to resource (e.g., /attributes/location or /features/temp)
- `value` (optional): The value to set (not needed for retrieve/delete commands)
- `correlation_id` (optional): Optional correlation ID for request tracking

**Example:**
```
Use the create_ditto_command tool to creates a ditto protocol command message for modifying thing state (modify, create, delete, retrieve).
```

### create_ditto_event

Creates a Ditto protocol event message for notifying about thing state changes.

**Parameters:**
- `thing_id` (required): The thing ID in format namespace:name
- `event_type` (required): Event type: created, modified, deleted
- `channel` (optional): Communication channel: twin or live
- `path` (optional): Path to changed resource
- `value` (required): The changed value
- `revision` (optional): Thing revision number

**Example:**
```
Use the create_ditto_event tool to creates a ditto protocol event message for notifying about thing state changes.
```

### create_ditto_feature

Creates a Ditto feature definition with properties and desired properties for IoT device capabilities.

**Parameters:**
- `feature_id` (required): Unique identifier for the feature (e.g., temperature, humidity)
- `properties` (optional): Current property values of the feature
- `desired_properties` (optional): Desired property values for the feature
- `definition` (optional): Array of definition identifiers (e.g., ['org.example:TemperatureSensor:1.0.0'])

**Example:**
```
Use the create_ditto_feature tool to creates a ditto feature definition with properties and desired properties for iot device capabilities.
```

### send_ditto_http_request

Sends an HTTP request to Eclipse Ditto REST API for thing management operations.

**Parameters:**
- `base_url` (required): Base URL of Ditto API (e.g., http://localhost:8080/api/2)
- `endpoint` (required): API endpoint path (e.g., /things/namespace:thing-1)
- `method` (optional): HTTP method: GET, POST, PUT, PATCH, DELETE
- `auth` (optional): Authentication credentials with username and password
- `payload` (optional): Request body payload
- `headers` (optional): Additional HTTP headers

**Example:**
```
Use the send_ditto_http_request tool to sends an http request to eclipse ditto rest api for thing management operations.
```

### create_ditto_policy

Creates an Eclipse Ditto policy for fine-grained access control on things and their resources.

**Parameters:**
- `policy_id` (required): Unique policy identifier in format namespace:name
- `entries` (required): Policy entries mapping labels to subjects and resources with permissions

**Example:**
```
Use the create_ditto_policy tool to creates an eclipse ditto policy for fine-grained access control on things and their resources.
```

### validate_ditto_message

Validates an Eclipse Ditto protocol message against the protocol specification.

**Parameters:**
- `message` (required): The Ditto protocol message to validate

**Example:**
```
Use the validate_ditto_message tool to validates an eclipse ditto protocol message against the protocol specification.
```

### subscribe_ditto_websocket

Establishes a WebSocket connection to Eclipse Ditto for real-time streaming of thing events and messages.

**Parameters:**
- `ws_url` (required): WebSocket URL (e.g., ws://localhost:8080/ws/2)
- `auth` (optional): Authentication credentials with username and password
- `filter` (optional): Optional RQL filter for message filtering (e.g., like(thingId,'namespace:*'))
- `namespaces` (optional): Array of namespaces to subscribe to

**Example:**
```
Use the subscribe_ditto_websocket tool to establishes a websocket connection to eclipse ditto for real-time streaming of thing events and messages.
```

## Setup

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "dittomcp": {
      "command": "python",
      "args": ["path/to/server.py"]
    }
  }
}
```
