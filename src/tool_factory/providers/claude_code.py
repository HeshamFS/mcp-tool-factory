"""Claude Code (Claude Agent SDK) provider implementation."""

import asyncio
import logging
from typing import Any

from tool_factory.providers.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class ClaudeCodeProvider(BaseLLMProvider):
    """Provider for Claude using the Claude Agent SDK.

    The Claude Agent SDK (formerly Claude Code SDK) is designed for agentic workflows.
    We configure it for raw text generation by:
    - Disabling all tools (allowed_tools=[])
    - Limiting to single turn (max_turns=1)
    - Using custom system_prompt
    """

    def _initialize_client(self) -> None:
        """Initialize the Claude Agent SDK environment."""
        import os

        # SDK reads CLAUDE_CODE_OAUTH_TOKEN from environment
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = self.api_key
        self._client = True  # Just a flag that we're initialized

    def _call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> LLMResponse:
        """Make API call using Claude Agent SDK."""
        # Run async query in sync context
        text = asyncio.run(self._async_query(system_prompt, user_prompt))

        return LLMResponse(
            text=text,
            tokens_in=None,  # SDK doesn't expose token counts
            tokens_out=None,
            model="claude-agent-sdk",
            raw_response=None,
        )

    async def _async_query(self, system_prompt: str, user_prompt: str) -> str:
        """Async query using Claude Agent SDK."""
        from claude_agent_sdk import query, ClaudeAgentOptions

        options = ClaudeAgentOptions(
            max_turns=1,
            allowed_tools=[],  # No tools, just text generation
            system_prompt=system_prompt,
        )

        result_text = ""
        async for message in query(prompt=user_prompt, options=options):
            # Handle structured output if available
            if hasattr(message, "structured_output") and message.structured_output:
                import json
                return json.dumps(message.structured_output)

            # Handle AssistantMessage with content blocks
            if hasattr(message, "content") and message.content:
                if isinstance(message.content, str):
                    result_text += message.content
                elif isinstance(message.content, list):
                    for block in message.content:
                        if hasattr(block, "text"):
                            result_text += block.text

        return result_text
