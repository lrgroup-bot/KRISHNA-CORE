from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = REPO_ROOT / "core"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from krishna_core.agentic_control_plane import AgenticPreToolPolicy


def main() -> int:
    raw = sys.stdin.read()
    payload = json.loads(raw or "{}")
    tool_name = payload.get("toolName") or payload.get("tool_name") or ""
    tool_args = payload.get("toolArgs")
    if tool_args is None:
        tool_args = payload.get("tool_input")
    decision = AgenticPreToolPolicy().evaluate(
        tool_name=str(tool_name),
        tool_args=tool_args,
        cwd=str(payload.get("cwd") or ""),
    )
    print(json.dumps(decision, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
