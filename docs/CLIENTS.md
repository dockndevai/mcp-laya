# Installing `mcp-laya` in your MCP client

`mcp-laya` is a **stdio** MCP server (Python). Any MCP-compatible agent can run it.

- **Recommended:** `pipx install mcp-laya`, then use the `mcp-laya` command.
- **From source:** `pip install -e .` in a venv, then `python -m mcp_laya`.

> First run downloads the Laya checkpoints once (downloads are off by default):
> `LAYA_ALLOW_DOWNLOAD=true python -c "import laya; laya.Router(preload=True)"`. After that it runs
> offline. See [`.env.example`](../.env.example) for every variable.

## Claude Code (CLI)

```bash
claude mcp add laya -- mcp-laya
```

Set options with `-e`, e.g. `claude mcp add laya -e LAYA_DEFAULT_MODEL=auto -e LAYA_MIN_CONFIDENCE=0.6 -- mcp-laya`.
List with `claude mcp list`, remove with `claude mcp remove laya`.

## Claude Desktop

Edit `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "laya": { "command": "mcp-laya", "env": { "LAYA_DEFAULT_MODEL": "auto" } }
  }
}
```

If `mcp-laya` isn't on the app's PATH, use the absolute path from `which mcp-laya`, or
`"command": "python", "args": ["-m", "mcp_laya"]` with the right interpreter.

## Cursor

`.cursor/mcp.json` (or `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "laya": { "command": "mcp-laya", "env": { "LAYA_DEFAULT_MODEL": "auto" } }
  }
}
```

## OpenAI Codex CLI

`~/.codex/config.toml`:

```toml
[mcp_servers.laya]
command = "mcp-laya"
env = { LAYA_DEFAULT_MODEL = "auto" }
```

## VS Code (Copilot / Agent mode)

`.vscode/mcp.json` (top-level key is `servers`):

```json
{
  "servers": {
    "laya": { "type": "stdio", "command": "mcp-laya", "env": { "LAYA_DEFAULT_MODEL": "auto" } }
  }
}
```

## Windsurf

`~/.codeium/windsurf/mcp_config.json` with the same `mcpServers` block as Cursor, then **Refresh**.

## Verify

On startup the server logs to **stderr**:

```
laya-mcp connected [models=english,multilingual,typed-decisions, default=auto, device=auto, offline=True]
```

Ask your agent to *"use laya to detect the language of this text"* (needs no model) or
*"classify this ticket's department with laya"* to confirm.
