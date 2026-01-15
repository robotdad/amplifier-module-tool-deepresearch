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
# Add the bundle from git
amplifier bundle add git+https://github.com/robotdad/amplifier-module-tool-deepresearch

# Set as active
amplifier bundle use deep-research

# Start interactive session
amplifier

# Or run a single prompt
amplifier run "Research the latest advances in quantum computing"
```

## Composing with Foundation

The root `bundle.md` provides just the tool and providers. To use with foundation, see `examples/deep-research-bundle.md`:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/robotdad/amplifier-module-tool-deepresearch@main
```

## Dependencies

This bundle includes enhanced provider modules with deep research support:

- `amplifier-module-provider-openai` (with background polling and native tools)
- `amplifier-module-provider-anthropic` (with native web search)

Currently using forks with these features:
- https://github.com/robotdad/amplifier-module-provider-openai (branch: feat/deep-research-support)
- https://github.com/robotdad/amplifier-module-provider-anthropic (branch: feat/native-web-search)

## License

MIT
