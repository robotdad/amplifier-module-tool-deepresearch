# amplifier-module-tool-deepresearch

Deep research tool for Amplifier - delegates to enhanced providers for AI-powered research.

> **Credit**: This work is based on initial research and implementation by [@michaeljabbour](https://github.com/michaeljabbour) in [amplifier-module-deepresearch](https://github.com/michaeljabbour/amplifier-module-deepresearch).

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
  "task_complexity": "medium",  // "low", "medium", or "high"
  "enable_code_interpreter": false  // OpenAI only
}
```

### Provider Selection

The tool automatically selects between OpenAI and Anthropic based on **provider priority** configured in your `~/.amplifier/settings.yaml`:

```yaml
config:
  providers:
  - config:
      api_key: ${ANTHROPIC_API_KEY}
      priority: 1        # Lower number = higher priority (this one wins)
    module: provider-anthropic
  - config:
      api_key: ${OPENAI_API_KEY}
      priority: 10       # Higher number = lower priority
    module: provider-openai
```

**How it works:**
- The tool reads the `priority` attribute from each mounted provider
- Lower number = higher precedence
- When you run `amplifier provider use anthropic`, it sets that provider's priority to 1
- No manual configuration needed if you use `amplifier provider use`

This means your research queries automatically use whichever provider you've configured as primary.

## Installation

The root bundle provides just the tool and providers (no orchestrator). It must be composed with foundation or another bundle that provides an orchestrator.

**Quickstart using the included example bundle:**

```bash
# Add the example bundle (includes foundation + deep-research)
amplifier bundle add "git+https://github.com/robotdad/amplifier-module-tool-deepresearch@main#subdirectory=examples"

# Set as active
amplifier bundle use deep-research-assistant

# Start interactive session
amplifier

# Or run a single prompt
amplifier run "Research the latest advances in quantum computing"
```

**Or compose it yourself:**

```bash
# 1. Add the deep-research bundle (tool + providers, no orchestrator)
amplifier bundle add git+https://github.com/robotdad/amplifier-module-tool-deepresearch

# 2. Create your own bundle that includes foundation + deep-research
```

```yaml
# my-research-bundle.md
includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/robotdad/amplifier-module-tool-deepresearch@main
```

```bash
# 3. Add and use your bundle
amplifier bundle add file://./my-research-bundle.md
amplifier bundle use my-research-bundle
amplifier
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
