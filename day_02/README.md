# Day 02: Hello World with YAML

Build your first AI agent with Gemini 3 in under 5 minutes without writing a single line of code.

## Learning Goals

- Understand ADK Agent Config (YAML-based agents)
- Create a simple agent using YAML configuration
- Use built-in tools like Google Search
- Run and test your agent with `adk web`

## Prerequisites

```bash
pip install google-adk
```

## Quick Start

### 1. Create a YAML-based Agent

Use the ADK CLI to create a config-based agent:

```bash
adk create my_agent --type=config
```

This generates:
- `my_agent/root_agent.yaml` - Agent configuration
- `my_agent/.env` - Environment variables

### 2. Basic YAML Structure

```yaml
name: assistant_agent
model: gemini-2.5-flash
description: A helper agent that can answer users' questions.
instruction: You are an agent to help answer users' various questions.
```

### 3. Run Your Agent

```bash
cd day-02
adk web
```

Open the browser and select your agent from the dropdown.

## YAML Configuration Options

| Field | Description |
|-------|-------------|
| `name` | Agent identifier |
| `model` | Gemini model to use (e.g., `gemini-2.5-flash`) |
| `description` | Brief description of the agent |
| `instruction` | System prompt / behavior instructions |
| `tools` | List of tools the agent can use |

## Built-in Tools

ADK supports these built-in tools:

- `google_search` - Search the web for information
- `code_execution` - Execute Python code
- `vertex_ai_search` - Search using Vertex AI

## Example: Agent with Google Search

See [root_agent.yaml](root_agent.yaml) for a working example.

```yaml
name: search_agent
model: gemini-2.5-flash
description: A helpful assistant that can search the web.
instruction: |
  You are a helpful assistant.
  Use Google Search for current events and factual information.
tools:
  - google_search
```

## Advanced: Mixing Python with YAML

You can add custom Python tools to your YAML agent:

1. Create `tools.py` in your agent folder:

```python
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"The weather in {city} is sunny."
```

2. Reference it in `root_agent.yaml`:

```yaml
tools:
  - google_search
  - tools.get_weather
```

## Advanced: MCP Server Integration

Connect to an MCP server for additional tools:

```yaml
tools:
  - type: MCPToolset
    stdio_server_params:
      command: uvx
      args:
        - mcp-server-time
```

## Limitations

- Currently only supports Gemini models
- Some advanced features require Python code
- Experimental feature - API may change

## Resources

- [ADK Agent Config Documentation](https://google.github.io/adk-docs/agents/config/)
- [2-Minute ADK: YAML Tutorial](https://medium.com/google-cloud/2-minute-adk-build-agents-the-easy-way-yaml-a55678d64a75)
- [Third Party MCP Tools in ADK](https://google.github.io/adk-docs/tools/third-party/)
- [ADK Samples Repository](https://github.com/google/adk-samples)

## Notes

Day 2 introduces the no-code approach to building agents using YAML configuration. This is the fastest way to prototype AI agents with Google ADK.
