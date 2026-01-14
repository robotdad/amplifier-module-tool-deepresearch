# amplifier-module-tool-deepresearch

Deep research tool for Amplifier - delegates to enhanced providers for AI-powered research.

## Overview

This tool provides a unified interface for AI-powered deep research, automatically selecting and configuring the appropriate provider based on availability and task requirements.

**Key design principles:**
- Delegates to mounted providers (does NOT create own API clients)
- Provider selection is configuration, not hardcoded heuristics
- Full observability via standard provider events

## Features

### Provider Support

| Provider | Features Used |
|----------|---------------|
| **OpenAI** | Deep research models (`o3-deep-research`, `o4-mini-deep-research`), background polling, native web search, code interpreter |
| **Anthropic** | Claude with native web search (`web_search_20250305`), extended thinking |

### Tool Input

```json
{
  "query": "Research question or topic",
  "provider": "auto",  // "openai", "anthropic", or "auto"
  "task_complexity": "medium",  // "low", "medium", or "high"
  "enable_code_interpreter": false  // OpenAI only
}
```

## Installation

```bash
uv pip install git+https://github.com/robotdad/amplifier-module-tool-deepresearch
```

## Configuration

```yaml
tools:
  deep_research:
    default_provider: auto  # or "openai" / "anthropic"
    timeout: 1800  # 30 minutes
    poll_interval: 5.0
```

## Dependencies

This module depends on enhanced provider modules with deep research support:

- `amplifier-module-provider-openai` (with background polling and native tools)
- `amplifier-module-provider-anthropic` (with native web search)

Currently using forks with these features:
- https://github.com/robotdad/amplifier-module-provider-openai (branch: feat/deep-research-support)
- https://github.com/robotdad/amplifier-module-provider-anthropic (branch: feat/native-web-search)

## License

MIT
