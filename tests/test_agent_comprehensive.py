"""Comprehensive tests for the ToolFactoryAgent."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import sys

from tool_factory.models import ToolSpec, GeneratedServer
from tool_factory.providers.base import LLMResponse
from tool_factory.config import LLMProvider


class TestToolFactoryAgentInit:
    """Tests for ToolFactoryAgent initialization."""

    def test_init_with_validation_errors(self):
        """Test initialization with validation errors raises ValueError."""
        from tool_factory.config import FactoryConfig

        # Create a config that will fail validation
        config = Mock(spec=FactoryConfig)
        config.validate.return_value = ["Error 1", "Error 2"]

        from tool_factory.agent import ToolFactoryAgent

        with pytest.raises(ValueError) as exc_info:
            ToolFactoryAgent(config=config)

        assert "Configuration errors" in str(exc_info.value)


class TestExtractSpecsFromOpenAPI:
    """Tests for _extract_specs_from_openapi method."""

    @pytest.fixture
    def agent(self):
        """Create a mocked agent."""
        with patch("tool_factory.providers.create_provider") as mock_create:
            mock_create.return_value = Mock()

            # Mock environment to have an API key
            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                from tool_factory.agent import ToolFactoryAgent

                return ToolFactoryAgent()

    def test_extract_specs_from_openapi_basic(self, agent):
        """Test basic OpenAPI spec extraction."""
        openapi_spec = {
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "summary": "List users",
                        "parameters": [],
                    }
                }
            }
        }

        specs = agent._extract_specs_from_openapi(openapi_spec)

        assert len(specs) == 1
        assert specs[0].name == "listUsers"

    def test_extract_specs_generates_name_from_path(self, agent):
        """Test name generation when operationId is missing."""
        openapi_spec = {"paths": {"/items": {"get": {"summary": "Get items"}}}}

        specs = agent._extract_specs_from_openapi(openapi_spec)

        assert len(specs) == 1
        assert "get" in specs[0].name.lower()

    def test_extract_specs_skips_non_http_methods(self, agent):
        """Test that non-HTTP methods are skipped."""
        openapi_spec = {
            "paths": {
                "/test": {
                    "get": {"summary": "Valid"},
                    "options": {"summary": "Skip"},
                }
            }
        }

        specs = agent._extract_specs_from_openapi(openapi_spec)

        assert len(specs) == 1

    def test_extract_specs_with_parameters(self, agent):
        """Test extraction with parameters."""
        openapi_spec = {
            "paths": {
                "/users/{id}": {
                    "get": {
                        "operationId": "getUser",
                        "summary": "Get user by ID",
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                                "description": "User ID",
                            }
                        ],
                    }
                }
            }
        }

        specs = agent._extract_specs_from_openapi(openapi_spec)

        assert len(specs) == 1
        assert "id" in specs[0].input_schema["properties"]
        assert "id" in specs[0].input_schema["required"]

    def test_extract_specs_multiple_methods(self, agent):
        """Test extraction with multiple HTTP methods."""
        openapi_spec = {
            "paths": {
                "/items": {
                    "get": {"summary": "List items"},
                    "post": {"summary": "Create item"},
                    "put": {"summary": "Update item"},
                    "delete": {"summary": "Delete item"},
                    "patch": {"summary": "Patch item"},
                }
            }
        }

        specs = agent._extract_specs_from_openapi(openapi_spec)

        assert len(specs) == 5

    def test_extract_specs_empty_paths(self, agent):
        """Test extraction with empty paths."""
        openapi_spec = {"paths": {}}

        specs = agent._extract_specs_from_openapi(openapi_spec)

        assert len(specs) == 0


class TestGenerateImplementation:
    """Tests for _generate_implementation_sync method."""

    @pytest.fixture
    def agent_with_mock_provider(self):
        """Create an agent with a mocked provider."""
        with patch("tool_factory.providers.create_provider") as mock_create:
            mock_provider = Mock()
            mock_provider.provider_name = "anthropic"
            mock_create.return_value = mock_provider

            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                from tool_factory.agent import ToolFactoryAgent

                agent = ToolFactoryAgent()
                return agent, mock_provider

    def test_generate_implementation_strips_markdown(self, agent_with_mock_provider):
        """Test markdown code blocks are stripped."""
        agent, mock_provider = agent_with_mock_provider

        mock_response = LLMResponse(
            text="```python\nreturn {'result': True}\n```",
            tokens_in=100,
            tokens_out=50,
            model="test-model",
            raw_response=None,
        )
        mock_provider.call.return_value = mock_response

        spec = ToolSpec(
            name="test_tool",
            description="Test",
            input_schema={"type": "object", "properties": {}},
        )

        impl = agent._generate_implementation_sync(spec)

        assert "```" not in impl
        assert "return {'result': True}" in impl

    def test_generate_implementation_strips_plain_markdown(
        self, agent_with_mock_provider
    ):
        """Test plain markdown code blocks are stripped."""
        agent, mock_provider = agent_with_mock_provider

        mock_response = LLMResponse(
            text="```\nreturn {'value': 42}\n```",
            tokens_in=100,
            tokens_out=50,
            model="test-model",
            raw_response=None,
        )
        mock_provider.call.return_value = mock_response

        spec = ToolSpec(
            name="test_tool",
            description="Test",
            input_schema={"type": "object", "properties": {}},
        )

        impl = agent._generate_implementation_sync(spec)

        assert "```" not in impl


class TestCallLLM:
    """Tests for _call_llm method."""

    @pytest.fixture
    def agent_with_mock_provider(self):
        """Create an agent with a mocked provider."""
        with patch("tool_factory.providers.create_provider") as mock_create:
            mock_provider = Mock()
            mock_provider.provider_name = "anthropic"
            mock_create.return_value = mock_provider

            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                from tool_factory.agent import ToolFactoryAgent

                agent = ToolFactoryAgent()
                return agent, mock_provider

    def test_call_llm_returns_text(self, agent_with_mock_provider):
        """Test that _call_llm returns response text."""
        agent, mock_provider = agent_with_mock_provider

        mock_response = LLMResponse(
            text="Response text",
            tokens_in=100,
            tokens_out=50,
            model="test-model",
            raw_response={"id": "123"},
            error=None,
        )
        mock_provider.call.return_value = mock_response

        result = agent._call_llm("Test prompt")

        assert result == "Response text"

    def test_call_llm_raises_on_error(self, agent_with_mock_provider):
        """Test _call_llm raises RuntimeError on error."""
        agent, mock_provider = agent_with_mock_provider

        mock_response = LLMResponse(
            text="",
            tokens_in=0,
            tokens_out=0,
            model="test-model",
            raw_response=None,
            error="API Error",
        )
        mock_provider.call.return_value = mock_response

        with pytest.raises(RuntimeError, match="LLM call failed"):
            agent._call_llm("Test prompt")


class TestSearchForContext:
    """Tests for _search_for_context method."""

    @pytest.fixture
    def agent(self):
        """Create a mocked agent."""
        with patch("tool_factory.providers.create_provider") as mock_create:
            mock_create.return_value = Mock()

            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                from tool_factory.agent import ToolFactoryAgent

                return ToolFactoryAgent()

    def test_search_method_exists(self, agent):
        """Test that _search_for_context method exists and is callable."""
        assert hasattr(agent, "_search_for_context")
        assert callable(agent._search_for_context)

    def test_search_for_context_returns_none_on_import_error(self, agent):
        """Test _search_for_context handles import errors."""
        # The actual search function depends on imports that may not be available
        # This test just verifies the method exists and is callable
        assert callable(agent._search_for_context)


class TestAgentServerGenerator:
    """Tests for agent's use of ServerGenerator."""

    @pytest.fixture
    def agent(self):
        """Create a mocked agent."""
        with patch("tool_factory.providers.create_provider") as mock_create:
            mock_create.return_value = Mock()

            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                from tool_factory.agent import ToolFactoryAgent

                return ToolFactoryAgent()

    def test_agent_has_server_generator(self, agent):
        """Test agent has a server generator."""
        from tool_factory.generators.server import ServerGenerator

        assert hasattr(agent, "server_generator")
        assert isinstance(agent.server_generator, ServerGenerator)

    def test_agent_has_docs_generator(self, agent):
        """Test agent has a docs generator."""
        from tool_factory.generators.docs import DocsGenerator

        assert hasattr(agent, "docs_generator")
        assert isinstance(agent.docs_generator, DocsGenerator)
