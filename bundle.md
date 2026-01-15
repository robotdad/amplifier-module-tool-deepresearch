---
bundle:
  name: deep-research
  version: 0.1.0
  description: Deep research capability using enhanced providers with web search and background polling

providers:
  - module: provider-openai
    source: git+https://github.com/robotdad/amplifier-module-provider-openai@feat/deep-research-support
    config:
      # API key from environment: OPENAI_API_KEY

  - module: provider-anthropic
    source: git+https://github.com/robotdad/amplifier-module-provider-anthropic@feat/native-web-search
    config:
      # API key from environment: ANTHROPIC_API_KEY
      enable_web_search: true

tools:
  - module: tool-deepresearch
    source: git+https://github.com/robotdad/amplifier-module-tool-deepresearch
    config:
      default_provider: auto
      timeout: 1800
      poll_interval: 5.0
---

# Deep Research

Provides the `deep_research` tool for comprehensive AI-powered research.

## Capabilities

- **OpenAI**: Deep research models (o3/o4-mini-deep-research) with background polling, web search, code interpreter
- **Anthropic**: Claude with native web search for current information

## Usage

```
deep_research(
  query="Your research question",
  provider="auto",  # or "openai" / "anthropic"
  task_complexity="medium",  # "low", "medium", "high"
  enable_code_interpreter=false  # OpenAI only
)
```
