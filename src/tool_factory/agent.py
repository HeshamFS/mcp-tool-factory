"""Main Tool Factory Agent for generating MCP servers."""

import json
import logging
import time
from typing import Any

from tool_factory.config import FactoryConfig, LLMProvider, get_default_config

# Module logger
logger = logging.getLogger(__name__)
from tool_factory.execution_logger import ExecutionLogger
from tool_factory.generators.docs import DocsGenerator
from tool_factory.generators.server import ServerGenerator
from tool_factory.models import GeneratedServer, ToolSpec
from tool_factory.prompts import (
    EXTRACT_TOOLS_PROMPT,
    GENERATE_IMPLEMENTATION_PROMPT,
    SYSTEM_PROMPT,
)
from tool_factory.validation import (
    extract_json_from_response,
    parse_llm_tool_response,
    validate_tool_specs,
)


class ToolFactoryAgent:
    """
    Agent that generates MCP servers from various inputs.

    The factory can generate complete MCP servers from:
    - Natural language descriptions
    - OpenAPI specifications
    - Python function signatures

    Setup:
        # Option 1: Set environment variable
        export ANTHROPIC_API_KEY="your-api-key"

        # Option 2: Pass API key directly
        agent = ToolFactoryAgent(api_key="your-api-key")

        # Option 3: Use custom config
        from tool_factory.config import FactoryConfig, LLMProvider
        config = FactoryConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-sonnet-4-20250514",
            api_key="your-api-key"
        )
        agent = ToolFactoryAgent(config=config)

    Supported Models (Anthropic - Dec 2025):
        Claude 4.5 Series (Latest):
        - claude-sonnet-4-5-20241022 (recommended - best for agents & coding)
        - claude-opus-4-5-20251101 (most intelligent, released Nov 2025)
        - claude-haiku-4-5-20241022 (fastest, near-frontier)

        Claude 4 Series:
        - claude-sonnet-4-20250514 (fast, intelligent)
        - claude-opus-4-20250514 (world's best coding model)
    """

    def __init__(
        self,
        config: FactoryConfig | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """
        Initialize the Tool Factory Agent.

        Args:
            config: Full configuration object. If provided, api_key and model are ignored.
            api_key: Anthropic API key. If None, uses ANTHROPIC_API_KEY env var.
            model: Model to use. Defaults to claude-sonnet-4-20250514.

        Raises:
            ValueError: If API key is not set and not found in environment.
        """
        # Build config
        if config is not None:
            self.config = config
        else:
            self.config = get_default_config()
            if api_key:
                self.config.api_key = api_key
            if model:
                self.config.model = model

        # Validate config
        errors = self.config.validate()
        if errors:
            raise ValueError(
                "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            )

        # Initialize LLM provider using the new provider system
        from tool_factory.providers import create_provider

        self.provider = create_provider(
            provider=self.config.provider,
            api_key=self.config.api_key,
            model=self.config.model,
            temperature=self.config.temperature,
        )

        self.server_generator = ServerGenerator()
        self.docs_generator = DocsGenerator()

    def _search_for_context(
        self, description: str, logger: ExecutionLogger | None = None
    ) -> str | None:
        """Search the web for API documentation and examples.

        Uses the provider's native web search tool to gather context
        about APIs, libraries, and implementation patterns.

        Args:
            description: The tool description to research
            logger: Optional ExecutionLogger to record actual web requests

        Returns:
            String with relevant context or None if search fails
        """
        try:
            from tool_factory.web_search import (
                search_for_api_info_with_logging,
                _generate_search_queries,
            )

            queries = _generate_search_queries(description)
            if logger:
                logger.log_step(
                    "web_search_start",
                    f"Starting web search with {len(queries)} queries",
                )

            result = search_for_api_info_with_logging(
                description=description,
                provider=self.config.provider,
                api_key=self.config.api_key,
                model=self.config.model,
                logger=logger,
            )

            if logger:
                logger.log_step(
                    "web_search_complete",
                    f"Web search complete, got {len(result) if result else 0} chars",
                )

            return result
        except Exception as e:
            logger.warning(f"Web search failed: {e}", exc_info=True)
            if logger:
                logger.log_step("web_search_error", f"Web search failed: {e}")
            return None

    async def generate_from_description(
        self,
        description: str,
        server_name: str = "GeneratedToolServer",
        web_search: bool = False,
    ) -> GeneratedServer:
        """
        Generate a complete MCP server from a natural language description.

        Args:
            description: Natural language description of desired tools
            server_name: Name for the generated server
            web_search: If True, search the web for API docs and examples first

        Returns:
            GeneratedServer with all code and documentation
        """
        # Step 0: Optionally search web for more context
        enhanced_description = description
        if web_search:
            search_context = self._search_for_context(description)
            if search_context:
                enhanced_description = (
                    f"{description}\n\n## Research Context:\n{search_context}"
                )

        # Step 1: Extract tool specifications from description
        tool_specs = await self._extract_tool_specs(enhanced_description)

        # Step 2: Generate implementation for each tool
        implementations: dict[str, str] = {}
        for spec in tool_specs:
            impl = await self._generate_implementation(spec)
            implementations[spec.name] = impl

        # Step 3: Generate all artifacts
        return self._generate_artifacts(server_name, tool_specs, implementations)

    def generate_from_description_sync(
        self,
        description: str,
        server_name: str = "GeneratedToolServer",
        web_search: bool = False,
        auth_env_vars: list[str] | None = None,
        include_health_check: bool = True,
        production_config: Any = None,
    ) -> GeneratedServer:
        """
        Synchronous version of generate_from_description.

        Args:
            description: Natural language description of desired tools
            server_name: Name for the generated server
            web_search: If True, search the web for API docs and examples first
            auth_env_vars: List of environment variable names for API authentication
            include_health_check: If True, include a health check endpoint
            production_config: ProductionConfig for logging, metrics, rate limiting, retries

        Returns:
            GeneratedServer with all code and documentation
        """
        # Initialize execution logger - captures ACTUAL execution data
        logger = ExecutionLogger(
            server_name=server_name,
            provider=self.config.provider.value,
            model=self.config.model,
        )
        logger.original_description = description
        logger.web_search_enabled = web_search

        logger.log_step("init", f"Starting generation of {server_name}")

        # Step 0: Optionally search web for more context
        enhanced_description = description
        if web_search:
            logger.log_step("web_search", "Starting web research for API documentation")
            search_context = self._search_for_context(description, logger=logger)
            if search_context:
                enhanced_description = (
                    f"{description}\n\n## Research Context:\n{search_context}"
                )

        # Step 1: Extract tool specifications (with logging)
        logger.log_step("extract_specs", "Sending prompt to LLM for tool extraction")
        tool_specs = self._extract_tool_specs_sync(enhanced_description, logger=logger)
        logger.tools_generated = [spec.name for spec in tool_specs]

        # Step 2: Generate implementations (with logging)
        implementations: dict[str, str] = {}
        for spec in tool_specs:
            logger.log_step("implement", f"Generating implementation for {spec.name}")
            impl = self._generate_implementation_sync(spec, logger=logger)
            implementations[spec.name] = impl

        # Step 3: Generate all artifacts
        logger.log_step("artifacts", "Generating server files")

        return self._generate_artifacts(
            server_name,
            tool_specs,
            implementations,
            logger=logger,
            auth_env_vars=auth_env_vars or [],
            include_health_check=include_health_check,
            production_config=production_config,
        )

    async def generate_from_openapi(
        self,
        openapi_spec: dict[str, Any],
        base_url: str | None = None,
        server_name: str = "GeneratedAPIServer",
    ) -> GeneratedServer:
        """
        Generate MCP server from an OpenAPI specification.

        Enhanced generator with support for:
        - API Key authentication (header, query, cookie)
        - OAuth2 / Bearer token authentication
        - Request body parameters
        - Full error handling

        Args:
            openapi_spec: OpenAPI specification as dictionary
            base_url: Base URL for the API (auto-detected from spec if not provided)
            server_name: Name for the generated server

        Returns:
            GeneratedServer with all code and documentation
        """
        from tool_factory.openapi import OpenAPIServerGenerator

        # Use enhanced OpenAPI generator
        generator = OpenAPIServerGenerator(openapi_spec, base_url)

        # Generate server code
        server_code = generator.generate_server_code(server_name)

        # Get tool specs for documentation
        tool_specs = generator.get_tool_specs()

        # Get auth env vars
        auth_env_vars = generator.get_auth_env_vars()

        return GeneratedServer(
            name=server_name,
            server_code=server_code,
            tool_specs=tool_specs,
            test_code=self.server_generator.generate_tests(tool_specs),
            dockerfile=self.server_generator.generate_dockerfile(
                tool_specs, auth_env_vars
            ),
            readme=self.docs_generator.generate_readme(server_name, tool_specs),
            skill_file=self.docs_generator.generate_skill(server_name, tool_specs),
            pyproject_toml=self.server_generator.generate_pyproject(
                server_name, tool_specs
            ),
            github_actions=self.server_generator.generate_github_actions(
                server_name, tool_specs, auth_env_vars
            ),
        )

    def _generate_artifacts(
        self,
        server_name: str,
        tool_specs: list[ToolSpec],
        implementations: dict[str, str],
        logger: ExecutionLogger | None = None,
        auth_env_vars: list[str] | None = None,
        include_health_check: bool = True,
        production_config: Any = None,
    ) -> GeneratedServer:
        """Generate all server artifacts from specs and implementations."""
        return GeneratedServer(
            name=server_name,
            server_code=self.server_generator.generate_server_simple(
                server_name,
                tool_specs,
                implementations,
                auth_env_vars=auth_env_vars or [],
                include_health_check=include_health_check,
                production_config=production_config,
            ),
            tool_specs=tool_specs,
            test_code=self.server_generator.generate_tests(tool_specs),
            dockerfile=self.server_generator.generate_dockerfile(
                tool_specs, auth_env_vars or [], production_config
            ),
            readme=self.docs_generator.generate_readme(server_name, tool_specs),
            skill_file=self.docs_generator.generate_skill(server_name, tool_specs),
            pyproject_toml=self.server_generator.generate_pyproject(
                server_name, tool_specs
            ),
            github_actions=self.server_generator.generate_github_actions(
                server_name, tool_specs, auth_env_vars or []
            ),
            execution_log=logger,
        )

    async def _extract_tool_specs(self, description: str) -> list[ToolSpec]:
        """Extract tool specifications from natural language description."""
        return self._extract_tool_specs_sync(description)

    def _extract_tool_specs_sync(
        self, description: str, logger: ExecutionLogger | None = None
    ) -> list[ToolSpec]:
        """Synchronous extraction of tool specs with validation.

        Uses Pydantic validation to ensure LLM responses conform to expected schema.
        """
        prompt = EXTRACT_TOOLS_PROMPT.format(description=description)

        content = self._call_llm(prompt, logger=logger)

        # Parse the LLM response (handles markdown, JSON extraction)
        try:
            specs_data = parse_llm_tool_response(content)
        except ValueError as e:
            logger_module = logging.getLogger(__name__)
            logger_module.error(f"Failed to parse LLM response: {e}")
            raise

        # Validate with Pydantic
        try:
            validated_specs = validate_tool_specs(specs_data)
        except Exception as e:
            logger_module = logging.getLogger(__name__)
            logger_module.error(f"Tool spec validation failed: {e}")
            raise ValueError(f"Invalid tool specifications: {e}")

        # Convert to ToolSpec model objects
        return [
            ToolSpec(
                name=spec.name,
                description=spec.description,
                input_schema=spec.input_schema,
                output_schema=spec.output_schema,
                implementation_hints=spec.implementation_hints,
                dependencies=spec.dependencies,
            )
            for spec in validated_specs
        ]

    async def _generate_implementation(self, spec: ToolSpec) -> str:
        """Generate implementation for a single tool."""
        return self._generate_implementation_sync(spec)

    def _generate_implementation_sync(
        self, spec: ToolSpec, logger: ExecutionLogger | None = None
    ) -> str:
        """Synchronous implementation generation."""
        prompt = GENERATE_IMPLEMENTATION_PROMPT.format(
            name=spec.name,
            description=spec.description,
            input_schema=json.dumps(spec.input_schema, indent=2),
            output_schema=(
                json.dumps(spec.output_schema, indent=2) if spec.output_schema else "{}"
            ),
            hints=spec.implementation_hints or "None provided",
            dependencies=", ".join(spec.dependencies) if spec.dependencies else "None",
        )

        content = self._call_llm(prompt, max_tokens=2048, logger=logger)

        # Clean up markdown code blocks if present
        if "```python" in content:
            content = content.split("```python")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return content.strip()

    def _call_llm(
        self, prompt: str, max_tokens: int = 4096, logger: ExecutionLogger | None = None
    ) -> str:
        """Call the LLM with the given prompt using the provider abstraction.

        This method delegates to the configured provider and handles logging.
        """
        # Use the provider abstraction
        response = self.provider.call(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=max_tokens,
        )

        # Check for errors
        if response.error:
            raise RuntimeError(f"LLM call failed: {response.error}")

        # Log the call if logger is provided
        if logger:
            logger.log_llm_call(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                raw_response=response.text,
                request_params={
                    "model": self.config.model,
                    "max_tokens": max_tokens,
                    "provider": self.provider.provider_name,
                },
                response_object=response.raw_response,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                latency_ms=response.latency_ms,
                error=response.error,
                error_traceback=response.error_traceback,
            )

        return response.text

    def _extract_specs_from_openapi(
        self,
        openapi_spec: dict[str, Any],
    ) -> list[ToolSpec]:
        """Extract tool specifications from OpenAPI spec for documentation."""
        tool_specs = []

        paths = openapi_spec.get("paths", {})
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    continue

                # Create tool name from operationId or path
                operation_id = operation.get("operationId")
                if operation_id:
                    name = operation_id
                else:
                    # Generate name from path and method
                    name = f"{method}_{path.replace('/', '_').strip('_')}"
                    name = name.replace("{", "").replace("}", "")

                # Build input schema from parameters
                input_schema: dict[str, Any] = {
                    "type": "object",
                    "properties": {},
                    "required": [],
                }

                for param in operation.get("parameters", []):
                    param_name = param.get("name", "")
                    param_schema = param.get("schema", {"type": "string"})
                    input_schema["properties"][param_name] = {
                        "type": param_schema.get("type", "string"),
                        "description": param.get("description", ""),
                    }
                    if param.get("required", False):
                        input_schema["required"].append(param_name)

                tool_specs.append(
                    ToolSpec(
                        name=name,
                        description=operation.get(
                            "summary", operation.get("description", "")
                        ),
                        input_schema=input_schema,
                        dependencies=["httpx"],
                    )
                )

        return tool_specs
