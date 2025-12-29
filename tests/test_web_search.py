"""Comprehensive tests for web_search module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from tool_factory.web_search import (
    SearchResult,
    WebSearcher,
    search_for_api_info,
    search_for_api_info_with_logging,
    _generate_search_queries,
)
from tool_factory.config import LLMProvider


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_create_search_result(self):
        """Test creating a SearchResult."""
        result = SearchResult(
            query="test query",
            content="Test content",
            sources=[{"url": "https://example.com", "title": "Example"}],
            raw_api_request={"model": "test"},
            raw_api_response={"id": "123"},
        )
        assert result.query == "test query"
        assert result.content == "Test content"
        assert len(result.sources) == 1
        assert result.sources[0]["url"] == "https://example.com"

    def test_search_result_defaults(self):
        """Test SearchResult with default values."""
        result = SearchResult(query="test", content="content")
        assert result.sources == []
        assert result.raw_api_request == {}
        assert result.raw_api_response == {}


class TestWebSearcher:
    """Tests for WebSearcher class."""

    def test_init(self):
        """Test WebSearcher initialization."""
        searcher = WebSearcher(
            provider=LLMProvider.ANTHROPIC,
            api_key="test-key",
            model="test-model",
        )
        assert searcher.provider == LLMProvider.ANTHROPIC
        assert searcher.api_key == "test-key"
        assert searcher.model == "test-model"

    def test_init_without_model(self):
        """Test WebSearcher without model."""
        searcher = WebSearcher(
            provider=LLMProvider.OPENAI,
            api_key="test-key",
        )
        assert searcher.model is None

    def test_search_unsupported_provider(self):
        """Test search with unsupported provider raises error."""
        # Create a mock provider that's not in the switch
        searcher = WebSearcher(
            provider=Mock(),  # Invalid provider
            api_key="test-key",
        )
        with pytest.raises(ValueError, match="Unsupported provider"):
            searcher.search("test query")

    def test_search_anthropic(self):
        """Test Anthropic web search."""
        import sys

        # Setup mock response
        mock_block = Mock()
        mock_block.type = "text"
        mock_block.text = "Search result content"
        mock_block.citations = []

        mock_response = Mock()
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.model = "claude-sonnet-4-5-20241022"
        mock_response.stop_reason = "end_turn"
        mock_response.content = [mock_block]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response

        mock_anthropic = Mock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            searcher = WebSearcher(
                provider=LLMProvider.ANTHROPIC,
                api_key="test-key",
            )
            result = searcher.search("test query", max_results=5)

            assert result.query == "test query"
            assert result.content == "Search result content"
            assert "model" in result.raw_api_request
            mock_client.messages.create.assert_called_once()

    def test_search_anthropic_with_citations(self):
        """Test Anthropic search with citations."""
        import sys

        mock_citation = Mock()
        mock_citation.url = "https://example.com"
        mock_citation.title = "Example"
        mock_citation.snippet = "A snippet"

        mock_block = Mock()
        mock_block.type = "text"
        mock_block.text = "Content with citations"
        mock_block.citations = [mock_citation]

        mock_response = Mock()
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.model = "claude-sonnet-4-5-20241022"
        mock_response.stop_reason = "end_turn"
        mock_response.content = [mock_block]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response

        mock_anthropic = Mock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            searcher = WebSearcher(
                provider=LLMProvider.ANTHROPIC,
                api_key="test-key",
            )
            result = searcher.search("test query")

            assert len(result.sources) == 1
            assert result.sources[0]["url"] == "https://example.com"
            assert result.sources[0]["title"] == "Example"

    def test_search_openai(self):
        """Test OpenAI web search."""
        import sys

        mock_response = Mock()
        mock_response.output_text = "OpenAI search result"
        mock_response.citations = []
        mock_response.id = "resp_123"
        mock_response.model = "gpt-4o-search-preview"
        mock_response.created = 1234567890
        mock_response.status = "completed"

        mock_client = Mock()
        mock_client.responses.create.return_value = mock_response

        mock_openai = Mock()
        mock_openai.OpenAI.return_value = mock_client

        with patch.dict(sys.modules, {"openai": mock_openai}):
            searcher = WebSearcher(
                provider=LLMProvider.OPENAI,
                api_key="test-key",
            )
            result = searcher.search("test query")

            assert result.query == "test query"
            assert result.content == "OpenAI search result"
            mock_client.responses.create.assert_called_once()

    def test_search_openai_with_citations(self):
        """Test OpenAI search with citations."""
        import sys

        mock_citation = Mock()
        mock_citation.url = "https://openai.com"
        mock_citation.title = "OpenAI Docs"
        mock_citation.snippet = "Documentation"

        mock_response = Mock()
        mock_response.output_text = "Result with sources"
        mock_response.citations = [mock_citation]
        mock_response.id = "resp_123"

        mock_client = Mock()
        mock_client.responses.create.return_value = mock_response

        mock_openai = Mock()
        mock_openai.OpenAI.return_value = mock_client

        with patch.dict(sys.modules, {"openai": mock_openai}):
            searcher = WebSearcher(
                provider=LLMProvider.OPENAI,
                api_key="test-key",
            )
            result = searcher.search("test query")

            assert len(result.sources) == 1
            assert result.sources[0]["url"] == "https://openai.com"

    def test_search_google(self):
        """Test Google web search."""
        import sys

        # Create mock candidate without grounding metadata
        mock_candidate = Mock()
        mock_candidate.grounding_metadata = None

        mock_response = Mock()
        mock_response.text = "Google search result"
        mock_response.candidates = [mock_candidate]

        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response

        mock_genai = Mock()
        mock_genai.GenerativeModel.return_value = mock_model

        # Must mock both parent 'google' module and 'google.generativeai'
        mock_google = Mock()
        mock_google.generativeai = mock_genai

        with patch.dict(
            sys.modules, {"google": mock_google, "google.generativeai": mock_genai}
        ):
            searcher = WebSearcher(
                provider=LLMProvider.GOOGLE,
                api_key="test-key",
            )
            result = searcher.search("test query")

            assert result.query == "test query"
            assert result.content == "Google search result"
            mock_genai.configure.assert_called_once_with(api_key="test-key")

    def test_search_google_with_grounding(self):
        """Test Google search with grounding metadata."""
        import sys

        # Create mock grounding chunk with web source (per Google API docs)
        mock_web = Mock()
        mock_web.uri = "https://google.com"
        mock_web.title = "Google"

        mock_chunk = Mock()
        mock_chunk.web = mock_web

        mock_grounding = Mock()
        mock_grounding.grounding_chunks = [mock_chunk]
        mock_grounding.web_search_queries = ["test query"]
        mock_grounding.grounding_supports = []

        mock_candidate = Mock()
        mock_candidate.grounding_metadata = mock_grounding

        mock_response = Mock()
        mock_response.text = "Grounded result"
        mock_response.candidates = [mock_candidate]

        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response

        mock_genai = Mock()
        mock_genai.GenerativeModel.return_value = mock_model

        # Must mock both parent 'google' module and 'google.generativeai'
        mock_google = Mock()
        mock_google.generativeai = mock_genai

        with patch.dict(
            sys.modules, {"google": mock_google, "google.generativeai": mock_genai}
        ):
            searcher = WebSearcher(
                provider=LLMProvider.GOOGLE,
                api_key="test-key",
            )
            result = searcher.search("test query")

            assert len(result.sources) == 1
            assert result.sources[0]["url"] == "https://google.com"
            assert result.sources[0]["title"] == "Google"

    def test_search_claude_code(self):
        """Test Claude Code web search."""
        import sys
        import asyncio as real_asyncio

        # Mock the SDK modules
        mock_sdk = Mock()
        mock_options = Mock()
        mock_sdk.ClaudeAgentOptions = mock_options

        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = ("Claude Code result", [{"type": "message"}])

                searcher = WebSearcher(
                    provider=LLMProvider.CLAUDE_CODE,
                    api_key="test-token",
                )
                result = searcher.search("test query")

                assert result.query == "test query"
                assert result.content == "Claude Code result"
                mock_run.assert_called_once()


class TestSearchForApiInfo:
    """Tests for search_for_api_info function."""

    @patch("tool_factory.web_search.WebSearcher")
    def test_search_for_api_info_success(self, mock_searcher_class):
        """Test successful API info search."""
        mock_searcher = Mock()
        mock_result = SearchResult(
            query="weather API",
            content="Weather API documentation",
            sources=[{"url": "https://weather.api"}],
        )
        mock_searcher.search.return_value = mock_result
        mock_searcher_class.return_value = mock_searcher

        result = search_for_api_info(
            description="Get weather data",
            provider=LLMProvider.ANTHROPIC,
            api_key="test-key",
        )

        assert "weather API" in result or "Weather API documentation" in result
        mock_searcher.search.assert_called()

    @patch("tool_factory.web_search.WebSearcher")
    def test_search_for_api_info_with_sources(self, mock_searcher_class):
        """Test API info search includes sources."""
        mock_searcher = Mock()
        mock_result = SearchResult(
            query="stock API",
            content="Stock price API docs",
            sources=[{"url": "https://stock.api"}, {"url": "https://finance.api"}],
        )
        mock_searcher.search.return_value = mock_result
        mock_searcher_class.return_value = mock_searcher

        result = search_for_api_info(
            description="Get stock prices",
            provider=LLMProvider.OPENAI,
            api_key="test-key",
        )

        assert "Sources:" in result
        mock_searcher.search.assert_called()

    @patch("tool_factory.web_search.WebSearcher")
    def test_search_for_api_info_handles_failure(self, mock_searcher_class):
        """Test API info search handles failures gracefully."""
        mock_searcher = Mock()
        mock_searcher.search.side_effect = Exception("Network error")
        mock_searcher_class.return_value = mock_searcher

        result = search_for_api_info(
            description="Some API",
            provider=LLMProvider.ANTHROPIC,
            api_key="test-key",
        )

        assert "Search failed" in result
        assert "Network error" in result

    @patch("tool_factory.web_search.WebSearcher")
    def test_search_for_api_info_limits_queries(self, mock_searcher_class):
        """Test that search limits to 3 queries."""
        mock_searcher = Mock()
        mock_result = SearchResult(query="test", content="content", sources=[])
        mock_searcher.search.return_value = mock_result
        mock_searcher_class.return_value = mock_searcher

        search_for_api_info(
            description="weather stock geocoding database email file",
            provider=LLMProvider.ANTHROPIC,
            api_key="test-key",
        )

        # Should be called at most 3 times
        assert mock_searcher.search.call_count <= 3


class TestSearchForApiInfoWithLogging:
    """Tests for search_for_api_info_with_logging function."""

    @patch("tool_factory.web_search.WebSearcher")
    def test_with_logging_success(self, mock_searcher_class):
        """Test search with logging on success."""
        mock_searcher = Mock()
        mock_result = SearchResult(
            query="test",
            content="Result content",
            sources=[{"url": "https://example.com"}],
            raw_api_request={"model": "test"},
            raw_api_response={"id": "123"},
        )
        mock_searcher.search.return_value = mock_result
        mock_searcher_class.return_value = mock_searcher

        mock_logger = Mock()

        result = search_for_api_info_with_logging(
            description="test description",
            provider=LLMProvider.ANTHROPIC,
            api_key="test-key",
            logger=mock_logger,
        )

        assert "Result content" in result
        mock_logger.log_web_search.assert_called()

    @patch("tool_factory.web_search.WebSearcher")
    def test_with_logging_on_error(self, mock_searcher_class):
        """Test search with logging on error."""
        mock_searcher = Mock()
        mock_searcher.search.side_effect = Exception("API error")
        mock_searcher_class.return_value = mock_searcher

        mock_logger = Mock()

        result = search_for_api_info_with_logging(
            description="test",
            provider=LLMProvider.ANTHROPIC,
            api_key="test-key",
            logger=mock_logger,
        )

        assert "Search failed" in result
        mock_logger.log_web_search.assert_called()
        # Check error was logged
        call_kwargs = mock_logger.log_web_search.call_args[1]
        assert "error" in call_kwargs

    @patch("tool_factory.web_search.WebSearcher")
    def test_with_logging_no_logger(self, mock_searcher_class):
        """Test search without logger still works."""
        mock_searcher = Mock()
        mock_result = SearchResult(query="test", content="content", sources=[])
        mock_searcher.search.return_value = mock_result
        mock_searcher_class.return_value = mock_searcher

        result = search_for_api_info_with_logging(
            description="test",
            provider=LLMProvider.ANTHROPIC,
            api_key="test-key",
            logger=None,
        )

        assert "content" in result

    @patch("tool_factory.web_search.WebSearcher")
    def test_with_logging_custom_model(self, mock_searcher_class):
        """Test search with custom model."""
        mock_searcher = Mock()
        mock_result = SearchResult(query="test", content="content", sources=[])
        mock_searcher.search.return_value = mock_result
        mock_searcher_class.return_value = mock_searcher

        search_for_api_info_with_logging(
            description="test",
            provider=LLMProvider.ANTHROPIC,
            api_key="test-key",
            model="custom-model",
        )

        mock_searcher_class.assert_called_with(
            LLMProvider.ANTHROPIC, "test-key", "custom-model"
        )


class TestGenerateSearchQueries:
    """Tests for _generate_search_queries function."""

    def test_weather_query(self):
        """Test weather keyword generates weather query."""
        queries = _generate_search_queries("Get weather data from API")
        assert any("weather" in q.lower() for q in queries)

    def test_stock_query(self):
        """Test stock keyword generates stock query."""
        queries = _generate_search_queries("Fetch stock prices")
        assert any("stock" in q.lower() for q in queries)

    def test_finance_query(self):
        """Test finance keyword generates stock query."""
        queries = _generate_search_queries(
            "Finance data service"
        )  # Use "finance" not "financial"
        assert any("stock" in q.lower() or "finance" in q.lower() for q in queries)

    def test_geocoding_query(self):
        """Test geocoding keyword generates geocoding query."""
        queries = _generate_search_queries("Geocoding service for addresses")
        assert any("geocod" in q.lower() for q in queries)

    def test_location_query(self):
        """Test location keyword generates geocoding query."""
        queries = _generate_search_queries("Get location coordinates")
        assert any("geocod" in q.lower() or "location" in q.lower() for q in queries)

    def test_database_query(self):
        """Test database keyword generates database query."""
        queries = _generate_search_queries("Database connection tool")
        assert any("database" in q.lower() for q in queries)

    def test_email_query(self):
        """Test email keyword generates email query."""
        queries = _generate_search_queries("Send email notifications")
        assert any("email" in q.lower() for q in queries)

    def test_file_query(self):
        """Test file keyword generates file query."""
        queries = _generate_search_queries("File upload handler")
        assert any("file" in q.lower() for q in queries)

    def test_general_query_always_added(self):
        """Test that a general query is always added."""
        queries = _generate_search_queries("Custom tool for something")
        # Should have at least one query
        assert len(queries) >= 1
        # Last query should be the general one
        assert "API documentation Python" in queries[-1]

    def test_multiple_keywords(self):
        """Test description with multiple keywords."""
        queries = _generate_search_queries("Weather and stock data with email alerts")
        assert len(queries) >= 3  # weather + stock + email + general

    def test_description_truncation(self):
        """Test long description is truncated in general query."""
        long_desc = "A" * 200
        queries = _generate_search_queries(long_desc)
        # General query should truncate to 100 chars
        general_query = queries[-1]
        assert len(general_query) < 200 + len(" API documentation Python")
