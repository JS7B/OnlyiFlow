"""通过 stdio 启动随插件分发的 OnlyiFlow MCP 服务器。"""

from __future__ import annotations

import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PLUGIN_ROOT / "src"

# 生成的宿主包为自包含结构，无需使用可编辑安装。
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from onlyiflow.mcp_server import mcp  # noqa: E402


if __name__ == "__main__":
    mcp.run()
