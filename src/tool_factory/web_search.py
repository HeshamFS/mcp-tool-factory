"""Web search capabilities for each LLM provider - captures FULL raw data.

Each provider has its own web search tool:
- Anthropic: web_search_20250305 tool ($10/1k searches)
- OpenAI: web_search tool with search-enabled models
- Google: google_search grounding tool ($14/1k queries)

References:
- https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/web-search-tool
- https://platform.openai.com/docs/guides/tools-web-search
- https://ai.google.dev/gemini-api/docs/google-search
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any

from .config import LLMProvider


@dataclass
class SearchResult:
    """Result from a web search - FULL DATA."""
    query: str
    content: str  # Full content - no truncation
    sources: list[dict[str, Any]] = field(default_factory=list)  # Full source data
    raw_api_request: dict[str, Any] = field(default_factory=dict)
    raw_api_response: dict[str, Any] = field(default_factory=dict)


class WebSearcher:
    """Web search handler for different LLM providers - captures FULL raw data."""

    def __init__(self, provider: LLMProvider, api_key: str, model: str | None = None):
        self.provider = provider
        self.api_key = api_key
        self.model = model

    def search(self, query: str, max_results: int = 5) -> SearchResult:
        """Perform a web search using the provider's native tool."""
        if self.provider == LLMProvider.ANTHROPIC:
            return self._search_anthropic(query, max_results)
        elif self.provider == LLMProvider.CLAUDE_CODE:
            return self._search_claude_code(query, max_results)
        elif self.provider == LLMProvider.OPENAI:
            return self._search_openai(query, max_results)
        elif self.provider == LLMProvider.GOOGLE:
            return self._search_google(query, max_results)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _search_anthropic(self, query: str, max_results: int) -> SearchResult:
        """Search using Anthropic's web_search tool - captures FULL data."""
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)

        # Build request
        api_request = {
            "model": self.model or "claude-sonnet-4-5-20241022",
            "max_tokens": 4096,
            "betas": ["web-search-2025-03-05"],
            "tools": [{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max_results,
            }],
            "messages": [{
                "role": "user",
                "content": f"Search the web for: {query}\n\nProvide a comprehensive summary of the most relevant information found."
            }],
        }

        response = client.messages.create(
            model=api_request["model"],
            max_tokens=api_request["max_tokens"],
            betas=api_request["betas"],
            tools=api_request["tools"],
            messages=api_request["messages"],
        )

        # Extract FULL content and sources
        content = ""
        sources = []
        raw_content_blocks = []

        for block in response.content:
            # Capture raw block data
            block_data = {"type": getattr(block, "type", "unknown")}

            if hasattr(block, "text"):
                content += block.text
                block_data["text"] = block.text

            if hasattr(block, "citations"):
                for citation in block.citations:
                    source_data = {}
                    if hasattr(citation, "url"):
                        source_data["url"] = citation.url
                    if hasattr(citation, "title"):
                        source_data["title"] = citation.title
                    if hasattr(citation, "snippet"):
                        source_data["snippet"] = citation.snippet
                    sources.append(source_data)
                block_data["citations"] = sources

            raw_content_blocks.append(block_data)

        # Build full response object
        api_response = {
            "id": response.id if hasattr(response, 'id') else None,
            "type": response.type if hasattr(response, 'type') else None,
            "role": response.role if hasattr(response, 'role') else None,
            "model": response.model if hasattr(response, 'model') else None,
            "stop_reason": response.stop_reason if hasattr(response, 'stop_reason') else None,
            "content": raw_content_blocks,
            "usage": {
                "input_tokens": response.usage.input_tokens if hasattr(response, 'usage') else None,
                "output_tokens": response.usage.output_tokens if hasattr(response, 'usage') else None,
            },
        }

        return SearchResult(
            query=query,
            content=content,
            sources=sources,
            raw_api_request=api_request,
            raw_api_response=api_response,
        )

    def _search_claude_code(self, query: str, max_results: int) -> SearchResult:
        """Search using Claude Code SDK - captures FULL data."""
        import asyncio
        from claude_agent_sdk import query as sdk_query, ClaudeAgentOptions

        api_request = {
            "max_turns": 1,
            "system_prompt": "You are a research assistant. Search the web and provide factual information with sources.",
            "prompt": f"Search the web for information about: {query}",
        }

        async def do_search():
            options = ClaudeAgentOptions(
                max_turns=1,
                system_prompt=api_request["system_prompt"],
            )

            result = ""
            raw_messages = []

            async for message in sdk_query(
                prompt=api_request["prompt"],
                options=options
            ):
                # Capture raw message
                msg_data = {"type": type(message).__name__}

                if hasattr(message, "content") and message.content:
                    if isinstance(message.content, list):
                        msg_data["content"] = []
                        for block in message.content:
                            if hasattr(block, "text"):
                                result += block.text
                                msg_data["content"].append({"type": "text", "text": block.text})
                    elif isinstance(message.content, str):
                        result += message.content
                        msg_data["content"] = message.content

                raw_messages.append(msg_data)

            return result, raw_messages

        content, raw_messages = asyncio.run(do_search())

        return SearchResult(
            query=query,
            content=content,
            sources=[],
            raw_api_request=api_request,
            raw_api_response={"messages": raw_messages},
        )

    def _search_openai(self, query: str, max_results: int) -> SearchResult:
        """Search using OpenAI's web_search tool - captures FULL data."""
        import openai

        client = openai.OpenAI(api_key=self.api_key)

        api_request = {
            "model": self.model or "gpt-4o-search-preview",
            "tools": [{
                "type": "web_search",
                "search_context_size": "medium",
            }],
            "input": f"Search the web for: {query}\n\nProvide a comprehensive summary.",
        }

        response = client.responses.create(
            model=api_request["model"],
            tools=api_request["tools"],
            input=api_request["input"],
        )

        content = response.output_text if hasattr(response, "output_text") else str(response)
        sources = []

        # Extract FULL citations
        if hasattr(response, "citations"):
            for c in response.citations:
                source_data = {}
                if hasattr(c, "url"):
                    source_data["url"] = c.url
                if hasattr(c, "title"):
                    source_data["title"] = c.title
                if hasattr(c, "snippet"):
                    source_data["snippet"] = c.snippet
                sources.append(source_data)

        # Build full response object
        api_response = {
            "output_text": content,
            "citations": sources,
        }
        # Add any other response attributes
        for attr in ['id', 'model', 'created', 'status']:
            if hasattr(response, attr):
                api_response[attr] = getattr(response, attr)

        return SearchResult(
            query=query,
            content=content,
            sources=sources,
            raw_api_request=api_request,
            raw_api_response=api_response,
        )

    def _search_google(self, query: str, max_results: int) -> SearchResult:
        """Search using Google's grounding with Google Search - captures FULL data."""
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)

        api_request = {
            "model_name": self.model or "gemini-2.0-flash",
            "tools": [{"google_search": {}}],
            "prompt": f"Search the web for: {query}\n\nProvide a comprehensive summary with sources.",
        }

        model = genai.GenerativeModel(
            model_name=api_request["model_name"],
            tools=api_request["tools"],
        )

        response = model.generate_content(api_request["prompt"])

        content = response.text if hasattr(response, "text") else str(response)
        sources = []

        # Extract FULL grounding sources
        if hasattr(response, "grounding_metadata"):
            grounding = response.grounding_metadata
            if isinstance(grounding, dict):
                for source in grounding.get("grounding_sources", []):
                    sources.append(source)  # Full source data
            api_response_grounding = grounding
        else:
            api_response_grounding = None

        # Build full response object
        api_response = {
            "text": content,
            "grounding_metadata": api_response_grounding,
        }
        # Add candidates if available
        if hasattr(response, "candidates"):
            try:
                api_response["candidates"] = str(response.candidates)
            except Exception:
                pass

        return SearchResult(
            query=query,
            content=content,
            sources=sources,
            raw_api_request=api_request,
            raw_api_response=api_response,
        )


def search_for_api_info(
    description: str,
    provider: LLMProvider,
    api_key: str,
    model: str | None = None,
) -> str:
    """Search for API documentation and implementation details.

    Args:
        description: The tool description to search for
        provider: LLM provider to use for search
        api_key: API key for the provider
        model: Optional model override

    Returns:
        String with relevant API information and examples
    """
    searcher = WebSearcher(provider, api_key, model)

    # Generate search queries based on description
    queries = _generate_search_queries(description)

    results = []
    for query in queries[:3]:  # Limit to 3 searches
        try:
            result = searcher.search(query)
            results.append(f"## {query}\n\n{result.content}")
            if result.sources:
                source_urls = [s.get("url", str(s)) for s in result.sources[:3]]
                results.append("Sources: " + ", ".join(source_urls))
        except Exception as e:
            results.append(f"Search failed for '{query}': {e}")

    return "\n\n".join(results)


def _generate_search_queries(description: str) -> list[str]:
    """Generate relevant search queries from a description."""
    queries = []

    # Extract potential API/service names
    keywords = ["API", "SDK", "library", "endpoint", "service"]
    desc_lower = description.lower()

    # Look for common patterns
    if "weather" in desc_lower:
        queries.append("free weather API documentation examples")
    if "stock" in desc_lower or "finance" in desc_lower:
        queries.append("free stock price API documentation")
    if "geocod" in desc_lower or "location" in desc_lower:
        queries.append("geocoding API documentation examples")
    if "database" in desc_lower:
        queries.append("database connection Python examples")
    if "email" in desc_lower:
        queries.append("email sending API Python examples")
    if "file" in desc_lower:
        queries.append("file operations Python best practices")

    # Add a general query based on description
    queries.append(f"{description[:100]} API documentation Python")

    return queries


def search_for_api_info_with_logging(
    description: str,
    provider: LLMProvider,
    api_key: str,
    model: str | None = None,
    logger: Any = None,
) -> str:
    """Search for API documentation with FULL execution logging.

    Args:
        description: The tool description to search for
        provider: LLM provider to use for search
        api_key: API key for the provider
        model: Optional model override
        logger: ExecutionLogger to record FULL raw data

    Returns:
        String with relevant API information and examples
    """
    searcher = WebSearcher(provider, api_key, model)
    queries = _generate_search_queries(description)

    results = []
    for query in queries[:3]:
        start_time = time.time()
        try:
            result = searcher.search(query)
            latency_ms = (time.time() - start_time) * 1000

            # Log the FULL web search with complete raw data
            if logger:
                logger.log_web_search(
                    provider=provider.value,
                    query=query,
                    raw_results=result.content,  # FULL - no truncation
                    sources=result.sources,  # FULL source data
                    api_request=result.raw_api_request,
                    api_response=result.raw_api_response,
                    latency_ms=latency_ms,
                )

            results.append(f"## {query}\n\n{result.content}")
            if result.sources:
                source_urls = [s.get("url", str(s)) for s in result.sources[:3]]
                results.append("Sources: " + ", ".join(source_urls))

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            if logger:
                logger.log_web_search(
                    provider=provider.value,
                    query=query,
                    raw_results="",
                    error=str(e),
                    latency_ms=latency_ms,
                )
            results.append(f"Search failed for '{query}': {e}")

    return "\n\n".join(results)
