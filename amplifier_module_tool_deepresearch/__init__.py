"""Deep research tool module for Amplifier.

Provides AI-powered deep research capability by delegating to enhanced providers
(OpenAI with background polling, Anthropic with native web search).

This is a THIN tool - it does not create its own API clients. Instead, it uses
mounted providers from the coordinator, following Amplifier's kernel philosophy
of mechanism over policy.
"""

__all__ = ["mount", "DeepResearchTool"]

# Amplifier module metadata
__amplifier_module_type__ = "tool"

import logging
from typing import Any

from amplifier_core import ConfigField, ModuleCoordinator, ToolResult
from amplifier_core.message_models import ChatRequest, Message

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_TIMEOUT = 1800  # 30 minutes for deep research
DEFAULT_POLL_INTERVAL = 5.0


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None):
    """
    Mount the deep research tool.

    Args:
        coordinator: Module coordinator with mounted providers
        config: Tool configuration

    Returns:
        Optional cleanup function
    """
    config = config or {}
    tool = DeepResearchTool(coordinator, config)
    await coordinator.mount("tools", tool, name="deep_research")
    logger.info("Mounted DeepResearchTool")
    return None


class DeepResearchTool:
    """Deep research tool that delegates to enhanced providers.

    This tool provides a unified interface for AI-powered deep research,
    automatically selecting and configuring the appropriate provider based
    on availability and task requirements.

    Key design principles:
    - Delegates to mounted providers (does NOT create own API clients)
    - Provider selection is configuration, not hardcoded heuristics
    - Full observability via standard provider events
    """

    name = "deep_research"
    description = (
        "Perform deep, comprehensive research on a topic using AI models with "
        "web search and extended reasoning capabilities. Use this tool when the "
        "user needs thorough research on a complex topic, multiple sources and "
        "perspectives are needed, the question requires extended reasoning, or "
        "web search would significantly improve the answer quality."
    )

    # Tool input schema for LLM
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The research question or topic to investigate thoroughly",
            },
            "provider": {
                "type": "string",
                "enum": ["openai", "anthropic", "auto"],
                "description": "Which provider to use. 'auto' selects based on availability.",
                "default": "auto",
            },
            "task_complexity": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Hint about task complexity to help with model selection",
                "default": "medium",
            },
            "enable_code_interpreter": {
                "type": "boolean",
                "description": "Enable code execution for data analysis (OpenAI only)",
                "default": False,
            },
        },
        "required": ["query"],
    }

    # Configuration fields exposed to users
    config_fields = [
        ConfigField(
            id="default_provider",
            display_name="Default Provider",
            field_type="choice",
            prompt="Which provider to use by default?",
            choices=["auto", "openai", "anthropic"],
            default="auto",
        ),
        ConfigField(
            id="timeout",
            display_name="Timeout",
            field_type="text",
            prompt="Maximum time to wait for research completion (seconds)",
            default=str(DEFAULT_TIMEOUT),
        ),
        ConfigField(
            id="poll_interval",
            display_name="Poll Interval",
            field_type="text",
            prompt="Polling interval for background requests (seconds)",
            default=str(DEFAULT_POLL_INTERVAL),
        ),
    ]

    def __init__(self, coordinator: ModuleCoordinator, config: dict[str, Any]):
        """Initialize the deep research tool.

        Args:
            coordinator: Module coordinator with mounted providers
            config: Tool configuration
        """
        self._coordinator = coordinator
        self._config = config
        self._default_provider = config.get("default_provider", "auto")
        self._timeout = config.get("timeout", DEFAULT_TIMEOUT)
        self._poll_interval = config.get("poll_interval", DEFAULT_POLL_INTERVAL)

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        """Execute deep research on the given query.

        Args:
            input: Tool input containing query and options

        Returns:
            ToolResult with research findings
        """
        query = input.get("query")
        if not query:
            return ToolResult(success=False, error="query is required")

        provider_choice = input.get("provider", self._default_provider)
        task_complexity = input.get("task_complexity", "medium")
        enable_code_interpreter = input.get("enable_code_interpreter", False)

        # Select provider
        provider, provider_name = await self._select_provider(provider_choice)
        if not provider:
            return ToolResult(
                success=False,
                error=f"No suitable provider available. Requested: {provider_choice}",
            )

        logger.info(f"Using provider '{provider_name}' for deep research")

        try:
            # Build and execute request based on provider
            if provider_name == "openai":
                result = await self._execute_openai(
                    provider, query, task_complexity, enable_code_interpreter
                )
            elif provider_name == "anthropic":
                result = await self._execute_anthropic(provider, query, task_complexity)
            else:
                return ToolResult(success=False, error=f"Unknown provider type: {provider_name}")

            return ToolResult(
                success=True,
                output=result,
                metadata={"provider": provider_name, "task_complexity": task_complexity},
            )

        except Exception as e:
            logger.exception(f"Deep research failed: {e}")
            return ToolResult(success=False, error=str(e))

    async def _select_provider(self, preference: str) -> tuple[Any | None, str | None]:
        """Select the best available provider.

        Args:
            preference: Provider preference (openai, anthropic, or auto)

        Returns:
            Tuple of (provider instance, provider name) or (None, None)
        """
        providers = self._coordinator.get_mounted("providers") or {}

        if preference == "auto":
            # Prefer OpenAI for deep research if available (has dedicated models)
            if "openai" in providers:
                return providers["openai"], "openai"
            if "anthropic" in providers:
                return providers["anthropic"], "anthropic"
            return None, None

        if preference in providers:
            return providers[preference], preference

        return None, None

    async def _execute_openai(
        self,
        provider: Any,
        query: str,
        task_complexity: str,
        enable_code_interpreter: bool,
    ) -> str:
        """Execute deep research using OpenAI provider.

        Uses deep research models with background polling and native tools.
        """
        # Select model based on complexity
        if task_complexity == "high":
            model = "o3-deep-research"
        else:
            model = "o4-mini-deep-research"

        # Build native tools
        tools = [{"type": "web_search_preview"}]
        if enable_code_interpreter:
            tools.append({"type": "code_interpreter"})

        # Build chat request
        request = ChatRequest(
            messages=[
                Message(
                    role="user",
                    content=(
                        "Please conduct thorough research on the following topic "
                        f"and provide a comprehensive analysis:\n\n{query}"
                    ),
                )
            ],
            model=model,
        )

        # Execute with background mode (auto-enabled for deep research models)
        response = await provider.complete(
            request,
            model=model,
            tools=tools,
            background=True,
            poll_interval=self._poll_interval,
            timeout=self._timeout,
        )

        # Extract text content from response
        return self._extract_response_text(response)

    async def _execute_anthropic(self, provider: Any, query: str, task_complexity: str) -> str:
        """Execute deep research using Anthropic provider.

        Uses Claude with native web search and extended thinking.
        """
        # Select model based on complexity
        if task_complexity == "high":
            model = "claude-sonnet-4-20250514"
        else:
            model = "claude-sonnet-4-20250514"  # Sonnet is good for most research

        # Build chat request with research prompt
        request = ChatRequest(
            messages=[
                Message(
                    role="user",
                    content=(
                        "Please conduct thorough research on the following topic "
                        "and provide a comprehensive analysis. Use web search to "
                        f"gather current information and cite your sources.\n\n{query}"
                    ),
                )
            ],
            model=model,
        )

        # Execute with web search enabled
        response = await provider.complete(
            request,
            model=model,
            enable_web_search=True,
            max_tokens=8192,  # Allow longer responses for research
        )

        # Extract text content, including any citations
        text = self._extract_response_text(response)

        # Append citations if available
        if hasattr(response, "web_search_results") and response.web_search_results:
            citations = self._format_citations(response.web_search_results)
            if citations:
                text += f"\n\n## Sources\n{citations}"

        return text

    def _extract_response_text(self, response: Any) -> str:
        """Extract text content from a chat response."""
        if hasattr(response, "content") and response.content:
            if isinstance(response.content, str):
                return response.content
            # Handle list of content blocks
            if isinstance(response.content, list):
                texts = []
                for block in response.content:
                    if hasattr(block, "text"):
                        texts.append(block.text)
                    elif isinstance(block, dict) and "text" in block:
                        texts.append(block["text"])
                return "\n".join(texts)
        if hasattr(response, "text") and response.text:
            return response.text
        return str(response)

    def _format_citations(self, web_search_results: list[dict]) -> str:
        """Format web search results as citations."""
        citations = []
        for i, result in enumerate(web_search_results, 1):
            title = result.get("title", "Unknown")
            url = result.get("url", "")
            if url:
                citations.append(f"{i}. [{title}]({url})")
            else:
                citations.append(f"{i}. {title}")
        return "\n".join(citations)
