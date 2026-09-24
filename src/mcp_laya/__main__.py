"""Entry point: `mcp-laya` / `python -m mcp_laya` — a stdio MCP server."""
from __future__ import annotations

import sys


def main() -> None:
    from .config import load_config
    from .server import _engine, mcp

    config = load_config()
    if config.preload:
        try:
            _engine.warmup()
        except Exception as e:
            sys.stderr.write(f"laya-mcp: preload failed ({e}); will load lazily on first call.\n")

    sys.stderr.write(
        f"laya-mcp connected [models={','.join(config.models)}, default={config.default_model}, "
        f"device={config.device}, offline={not config.allow_download}]\n"
    )
    mcp.run()


if __name__ == "__main__":
    main()
