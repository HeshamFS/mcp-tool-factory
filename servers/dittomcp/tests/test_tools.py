"""Auto-generated tests for MCP server."""

import json
import pytest
from mcp import Client


@pytest.fixture
async def mcp_client():
    """Create MCP client connected to server."""
    from server import mcp

    async with Client(transport=mcp) as client:
        yield client


@pytest.mark.asyncio
async def test_list_tools(mcp_client):
    """Verify all tools are registered."""
    tools = await mcp_client.list_tools()
    tool_names = [t.name for t in tools.tools]

    assert "create_ditto_message" in tool_names
    assert "create_ditto_thing" in tool_names
    assert "parse_ditto_message" in tool_names
    assert "create_ditto_command" in tool_names
    assert "create_ditto_event" in tool_names
    assert "create_ditto_feature" in tool_names
    assert "send_ditto_http_request" in tool_names
    assert "create_ditto_policy" in tool_names
    assert "validate_ditto_message" in tool_names
    assert "subscribe_ditto_websocket" in tool_names


@pytest.mark.asyncio
async def test_create_ditto_message_exists(mcp_client):
    """Test create_ditto_message tool is callable."""
    tools = await mcp_client.list_tools()
    tool = next((t for t in tools.tools if t.name == "create_ditto_message"), None)
    assert tool is not None
    assert tool.description == "Creates an Eclipse Ditto protocol message for sending commands or events to IoT devices."


@pytest.mark.asyncio
async def test_create_ditto_thing_exists(mcp_client):
    """Test create_ditto_thing tool is callable."""
    tools = await mcp_client.list_tools()
    tool = next((t for t in tools.tools if t.name == "create_ditto_thing"), None)
    assert tool is not None
    assert tool.description == "Creates a complete Eclipse Ditto Thing definition with attributes, features, and metadata."


@pytest.mark.asyncio
async def test_parse_ditto_message_exists(mcp_client):
    """Test parse_ditto_message tool is callable."""
    tools = await mcp_client.list_tools()
    tool = next((t for t in tools.tools if t.name == "parse_ditto_message"), None)
    assert tool is not None
    assert tool.description == "Parses an incoming Eclipse Ditto protocol message and extracts its components."


@pytest.mark.asyncio
async def test_create_ditto_command_exists(mcp_client):
    """Test create_ditto_command tool is callable."""
    tools = await mcp_client.list_tools()
    tool = next((t for t in tools.tools if t.name == "create_ditto_command"), None)
    assert tool is not None
    assert tool.description == "Creates a Ditto protocol command message for modifying thing state (modify, create, delete, retrieve)."


@pytest.mark.asyncio
async def test_create_ditto_event_exists(mcp_client):
    """Test create_ditto_event tool is callable."""
    tools = await mcp_client.list_tools()
    tool = next((t for t in tools.tools if t.name == "create_ditto_event"), None)
    assert tool is not None
    assert tool.description == "Creates a Ditto protocol event message for notifying about thing state changes."


@pytest.mark.asyncio
async def test_create_ditto_feature_exists(mcp_client):
    """Test create_ditto_feature tool is callable."""
    tools = await mcp_client.list_tools()
    tool = next((t for t in tools.tools if t.name == "create_ditto_feature"), None)
    assert tool is not None
    assert tool.description == "Creates a Ditto feature definition with properties and desired properties for IoT device capabilities."


@pytest.mark.asyncio
async def test_send_ditto_http_request_exists(mcp_client):
    """Test send_ditto_http_request tool is callable."""
    tools = await mcp_client.list_tools()
    tool = next((t for t in tools.tools if t.name == "send_ditto_http_request"), None)
    assert tool is not None
    assert tool.description == "Sends an HTTP request to Eclipse Ditto REST API for thing management operations."


@pytest.mark.asyncio
async def test_create_ditto_policy_exists(mcp_client):
    """Test create_ditto_policy tool is callable."""
    tools = await mcp_client.list_tools()
    tool = next((t for t in tools.tools if t.name == "create_ditto_policy"), None)
    assert tool is not None
    assert tool.description == "Creates an Eclipse Ditto policy for fine-grained access control on things and their resources."


@pytest.mark.asyncio
async def test_validate_ditto_message_exists(mcp_client):
    """Test validate_ditto_message tool is callable."""
    tools = await mcp_client.list_tools()
    tool = next((t for t in tools.tools if t.name == "validate_ditto_message"), None)
    assert tool is not None
    assert tool.description == "Validates an Eclipse Ditto protocol message against the protocol specification."


@pytest.mark.asyncio
async def test_subscribe_ditto_websocket_exists(mcp_client):
    """Test subscribe_ditto_websocket tool is callable."""
    tools = await mcp_client.list_tools()
    tool = next((t for t in tools.tools if t.name == "subscribe_ditto_websocket"), None)
    assert tool is not None
    assert tool.description == "Establishes a WebSocket connection to Eclipse Ditto for real-time streaming of thing events and messages."
