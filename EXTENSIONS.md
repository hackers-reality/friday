# FRIDAY Extensions & MCP

FRIDAY supports an extensible plugin system through the Extension Registry. This allows you to add new tools, connect external services, and run MCP (Model Context Protocol) servers.

## Extension Types

| Type | Description |
|------|-------------|
| `mcp` | Model Context Protocol server — provides tools/resources to the LLM via stdio |
| `tool` | Standalone tool plugin — exposes executable or script |
| `bridge` | External service bridge — connects to REST/gRPC/WebSocket APIs |
| `hook` | Event hook — reacts to FRIDAY lifecycle events |
| `adapter` | Provider adapter — adapts a new LLM provider |

## Managing Extensions

### Via CLI

```bash
# Register an HTTP extension
python -m friday.cli cfg
# Use the extension_registry_tool directly via FRIDAY voice/chat:
# "Register a tool extension at http://localhost:8081 for image processing"
```

### Via the `extension_registry_tool`

FRIDAY can manage extensions conversationally:

- "Register a new MCP server called filesystem that runs `npx @modelcontextprotocol/server-filesystem /path`"
- "List all registered extensions"
- "Check health of all extensions"
- "Find extensions with 'database' capabilities"

## MCP Server Setup

MCP servers run as subprocesses. FRIDAY manages their lifecycle through the Extension Registry.

### Registering an MCP Server

```bash
# Via extension_registry_tool (conversational):
# "Register MCP server: name=filesystem, command=npx, args=['@modelcontextprotocol/server-filesystem', '/data'], description='File system access'"
```

### Built-in MCP Support

FRIDAY's `mcp_tool` (already in live.py) provides runtime MCP protocol support. The Extension Registry manages the lifecycle and discovery of MCP servers.

## Health Checks

Extensions are health-checked through:
- **HTTP extensions**: HEAD/GET request to endpoint
- **TCP services**: Socket connection to host:port
- **MCP servers**: Subprocess spawn check

```bash
python -m friday.cli sc health  # Check sidecar health
# For extensions, use the tool conversationally
```

## Capability Discovery

FRIDAY can discover extensions by capability:

```
"What extensions do I have for file management?"
"Find tools that can process images"
"Show me all MCP servers"
```

This searches the Extension Registry's capability metadata.

## API for Programmatic Use

```python
from friday.extension_registry import (
    register_extension,
    list_extensions,
    check_extension_health,
    discover_capabilities,
    register_mcp_server,
)

# Register a tool
register_extension(
    name="image-processor",
    ext_type="tool",
    endpoint="http://localhost:8081",
    capabilities=["image_resize", "image_convert", "thumbnail"],
)

# Discover file-related capabilities
results = discover_capabilities("file")
```

## Custom Extension Development

To create a custom extension:

1. Implement an HTTP server (any framework) or a script that follows your protocol
2. Register it with FRIDAY via the `extension_registry_tool`
3. Define capabilities for discovery

For MCP servers, follow the [Model Context Protocol specification](https://modelcontextprotocol.io/).

## Registry Storage

Extensions are stored at `friday_memory/config/extension_registry.json`. You can edit this file directly but FRIDAY will overwrite changes on next tool call.
