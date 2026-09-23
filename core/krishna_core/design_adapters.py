from __future__ import annotations

"""Optional, zero-vendor-lock adapters for Sudarshan design tooling.

Adapters never become KRISHNA authority. They expose availability and bounded
execution only; provider output is untrusted evidence until verified.
"""

from dataclasses import asdict, dataclass
import shutil
import subprocess


@dataclass(frozen=True)
class ToolResult:
    tool: str
    available: bool
    ok: bool
    output: str = ""
    returncode: int | None = None

    def as_dict(self):
        return asdict(self)


class LocalToolAdapter:
    def __init__(self, command: str):
        self.command = str(command or "").strip()
        if not self.command:
            raise ValueError("tool command is required")

    def executable(self):
        return shutil.which(self.command)

    def available(self):
        return bool(self.executable())

    def run(self, args=(), timeout=120):
        exe = self.executable()
        if not exe:
            return ToolResult(self.command, False, False, "not installed", None)
        argv = [exe, *[str(x) for x in (args or [])]]
        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=max(1, min(int(timeout), 600)),
            shell=False,
        )
        output = ((proc.stdout or "") + (proc.stderr or ""))[-12000:]
        return ToolResult(self.command, True, proc.returncode == 0, output, proc.returncode)


class PlaywrightCLI(LocalToolAdapter):
    def __init__(self):
        super().__init__("playwright-cli")


class StagehandAdapter:
    """Optional agentic-browser helper. Disabled unless explicitly enabled."""

    def __init__(self, enabled=False):
        self.enabled = bool(enabled)

    def available(self):
        return self.enabled

    def status(self):
        return {
            "name": "stagehand",
            "available": self.enabled,
            "authority": "optional recovery/exploration adapter only",
            "canonical_browser": "Garudanetra/Playwright",
        }


class StorybookAdapter:
    REQUIRED_STATES = (
        "default", "hover", "focus", "disabled", "loading", "error",
        "empty", "long-text", "mobile",
    )

    def required_states(self):
        return self.REQUIRED_STATES

    def status(self):
        return {
            "name": "storybook",
            "required_states": list(self.REQUIRED_STATES),
            "project_supplies_runner": True,
            "authority": "component-state evidence only",
        }
