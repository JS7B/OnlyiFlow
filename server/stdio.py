"""Bootstrap the bundled OnlyiFlow MCP server over stdio."""

from __future__ import annotations

import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PLUGIN_ROOT / "src"

# Generated host packages are self-contained and do not require an editable install.
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from onlyiflow.mcp_server import mcp  # noqa: E402


if __name__ == "__main__":
    mcp.run()
