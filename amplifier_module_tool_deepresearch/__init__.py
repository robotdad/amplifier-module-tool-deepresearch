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
        "web search and extended reasoning capabilities. IMPORTANT: Before calling "
        "this tool, you MUST clarify the research request with the user - ask about "
        "scope (how broad/narrow), preferences (sources, perspectives), constraints "
        "(time period, geographic focus), and desired output format. Confirm the "
        "refined query with the user before proceeding, as research takes 10-15 "
        "minutes and is resource-intensive. Use this tool when the user needs "
        "thorough research on a complex topic, multiple sources and perspectives "
        "are needed, the question requires extended reasoning, or web search would "
        "significantly improve the answer quality."
    )

    # Tool input schema for LLM
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The research question or topic to investigate thoroughly",
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

        task_complexity = input.get("task_complexity", "medium")
        enable_code_interpreter = input.get("enable_code_interpreter", False)

        # Select provider based on what's mounted
        provider, provider_name, error = self._select_provider()
        if error:
            return ToolResult(success=False, error=error)
        if not provider:
            return ToolResult(
                success=False,
                error="No suitable provider available. Deep research requires OpenAI or Anthropic.",
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

    def _select_provider(self) -> tuple[Any | None, str | None, str | None]:
        """Select provider based on priority configuration.

        Uses the provider priority system - lower priority number means
        higher precedence. This respects the user's `amplifier provider use`
        configuration.

        Returns:
            Tuple of (provider instance, provider name, error message)
        """
        providers = self._coordinator.get("providers") or {}

        # Filter to supported providers only
        supported = ["anthropic", "openai"]
        available = {name: prov for name, prov in providers.items() if name in supported}

        if not available:
            mounted = list(providers.keys()) if providers else []
            return (
                None,
                None,
                (
                    f"Deep research requires OpenAI or Anthropic provider. "
                    f"Currently mounted: {mounted or 'none'}"
                ),
            )

        # Select by priority (lower number = higher priority, default 100)
        def get_priority(item: tuple[str, Any]) -> int:
            name, provider = item
            return getattr(provider, "priority", 100)

        sorted_providers = sorted(available.items(), key=get_priority)
        selected_name, selected_provider = sorted_providers[0]

        # Log selection for transparency
        priorities = {name: getattr(p, "priority", 100) for name, p in available.items()}
        logger.info(f"[DEEP_RESEARCH] Provider priorities: {priorities}, selected: {selected_name}")

        return selected_provider, selected_name, None

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

        # Deep research models need high token limits - reasoning consumes
        # significant tokens before content is produced. Without sufficient
        # budget, responses are truncated with empty content.
        # o3-deep-research: needs ~16k+ for reasoning + content
        # o4-mini-deep-research: needs ~12k+ for reasoning + content
        max_tokens = 16000 if task_complexity == "high" else 12000

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

        # Reasoning effort control: Deep research models share max_output_tokens
        # between reasoning AND visible output. Without effort control, the model
        # spends all tokens on reasoning before producing content.
        # Note: o3-deep-research only supports "medium", o4-mini supports "low"
        reasoning_effort = "medium" if model == "o3-deep-research" else "low"
        reasoning = {"effort": reasoning_effort, "summary": "auto"}

        # Execute with background mode (auto-enabled for deep research models)
        response = await provider.complete(
            request,
            model=model,
            tools=tools,
            background=True,
            poll_interval=self._poll_interval,
            timeout=self._timeout,
            max_tokens=max_tokens,
            max_tool_calls=20,  # Prevent excessive searching that consumes token budget
            reasoning=reasoning,  # Control reasoning token usage
        )

        # Extract text content from response, handling incomplete status
        return self._extract_response_with_status(response)

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

    def _extract_response_with_status(self, response: Any) -> str:
        """Extract text from response, handling incomplete status gracefully.

        Deep research can hit max_output_tokens, returning status='incomplete'.
        In this case, reasoning/thinking blocks may contain useful partial results.
        We extract what we can and note the incomplete status.
        """
        # Check for incomplete status in metadata
        is_incomplete = False
        incomplete_reason = None
        if hasattr(response, "metadata") and response.metadata:
            status = response.metadata.get("openai:status")
            if status == "incomplete":
                is_incomplete = True
                incomplete_reason = response.metadata.get("openai:incomplete_reason", "unknown")
                logger.warning(f"[DEEP_RESEARCH] Response incomplete: {incomplete_reason}")

        # Try to extract the main text content
        text = self._extract_response_text(response)

        # If we got content, return it (with note if incomplete)
        if text and text != str(response):
            if is_incomplete:
                text += (
                    f"\n\n---\n**Note:** This research response was truncated "
                    f"({incomplete_reason}). The analysis above may be partial. "
                    f"Consider refining your query for a more focused response."
                )
            return text

        # If no main text but incomplete, try to salvage from thinking blocks
        if is_incomplete:
            thinking_content = self._extract_thinking_summary(response)
            if thinking_content:
                return (
                    f"**Note:** Research hit output limits before producing final content. "
                    f"Below is a summary extracted from the reasoning process:\n\n"
                    f"{thinking_content}\n\n"
                    f"Consider refining your query for a complete response."
                )

        # Nothing useful found
        if is_incomplete:
            return (
                f"Research was incomplete ({incomplete_reason}) and no content could be extracted. "
                f"Try a more focused query or lower complexity setting."
            )

        return text

    def _extract_thinking_summary(self, response: Any) -> str | None:
        """Extract useful content from thinking/reasoning blocks as fallback.

        When main content is empty but thinking blocks exist, we can salvage
        partial insights from the reasoning process.
        """
        if not hasattr(response, "content_blocks") or not response.content_blocks:
            return None

        thinking_texts = []
        for block in response.content_blocks:
            # Check for thinking block type
            block_type = getattr(block, "type", None)
            if block_type in ("thinking", "reasoning"):
                text = getattr(block, "text", None) or getattr(block, "thinking", None)
                if text and len(text) > 100:  # Only include substantial blocks
                    # Take last portion as it's usually the most synthesized
                    thinking_texts.append(text[-2000:] if len(text) > 2000 else text)

        if not thinking_texts:
            return None

        # Return the last (most recent/synthesized) thinking block
        return thinking_texts[-1] if thinking_texts else None

    def _extract_response_text(self, response: Any) -> str:
        """Extract text content from a chat response.

        Per OpenAI docs: 'response.output_text is the safest way to retrieve
        the final human-readable answer.' We check this first before falling
        back to other extraction methods.
        """
        # Per OpenAI docs, output_text is the safest way to get the final answer
        if hasattr(response, "output_text") and response.output_text:
            return response.output_text

        # Fallback: check the text field (used by our ChatResponse)
        if hasattr(response, "text") and response.text:
            return response.text

        # Fallback: extract from content blocks
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
                if texts:
                    return "\n".join(texts)

        # Last resort: stringify the response
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
