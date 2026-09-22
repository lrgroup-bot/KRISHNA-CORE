from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import importlib.util
import os
import shutil

from .browser_operator import BrowserOperator
from .garudanetra_recovery import BrowserRecoveryAdapter
from .garudanetra_session import GarudanetraSessionManager


@dataclass(frozen=True)
class BrowserAdapter:
    name: str
    role: str
    capabilities: tuple[str, ...]
    discovered: bool
    configured: bool
    command: str | None = None
    note: str = ""

    def as_dict(self) -> dict:
        row=asdict(self)
        row["capabilities"]=list(self.capabilities)
        return row


class BrowserAdapterRegistry:
    """Inventory of optional browser implementations behind one KRISHNA boundary.

    Discovery never grants execution authority.  Playwright is the canonical runtime.
    External browser projects are optional adapters/candidate evidence providers and are
    only considered configured when an explicit KRISHNA_* environment command/endpoint
    is supplied or the executable is present on PATH.
    """

    SPECS=(
        ("browser_harness","recovery","KRISHNA_BROWSER_HARNESS_CMD","browser-harness",
         ("semantic_recovery","reusable_helpers","mcp"),"Browser Harness candidate recovery bridge"),
        ("agent_browser","observer/action","KRISHNA_AGENT_BROWSER_CMD","agent-browser",
         ("accessibility_refs","cdp","stream","webmcp"),"agent-browser optional CLI adapter"),
        ("browsercode","coding/action","KRISHNA_BROWSERCODE_CMD","bcode",
         ("cdp","browser_execute","reusable_scripts"),"BrowserCode optional coding-browser adapter"),
        ("opendevbrowser","observer/action","KRISHNA_OPENDEVBROWSER_CMD","opendevbrowser",
         ("accessibility_refs","cdp","active_tab","debug_trace"),"OpenDevBrowser optional adapter"),
        ("rustwright","engine","KRISHNA_RUSTWRIGHT_CMD","rustwright-cli",
         ("native_cdp","accessibility_refs","mcp"),"Rustwright experimental engine; never automatic"),
        ("lucarne","stream/control","KRISHNA_LUCARNE_CMD","lucarne",
         ("cdp","watch","takeover","record"),"Lucarne optional supervised-session adapter"),
        ("promptwright","record/replay","KRISHNA_PROMPTWRIGHT_CMD","promptwright",
         ("record","gherkin","replay","playwright"),"Promptwright optional workflow adapter"),
        ("skyvern","vision_recovery","KRISHNA_SKYVERN_CMD","skyvern",
         ("vision","workflow","playwright"),"Skyvern optional vision-fallback adapter"),
        ("rrweb","record/replay","KRISHNA_RRWEB_CMD","rrweb",
         ("record","replay","dom_events"),"rrweb optional replay adapter"),
    )

    def __init__(self,runtime_root:str|Path):
        self.runtime_root=Path(runtime_root).resolve()

    @staticmethod
    def _command(env_name,binary):
        explicit=str(os.getenv(env_name,"")).strip()
        if explicit:return explicit,True
        found=shutil.which(binary)
        return (found,False) if found else (None,False)

    def status(self)->dict:
        rows=[]
        playwright=importlib.util.find_spec("playwright") is not None
        rows.append(BrowserAdapter(
            "playwright","canonical_engine",
            ("chromium","cdp","console","network","screenshots","downloads","persistent_context"),
            playwright,playwright,None,
            "Canonical Garudanetra engine; other adapters do not silently replace it.",
        ).as_dict())
        for name,role,env_name,binary,caps,note in self.SPECS:
            command,explicit=self._command(env_name,binary)
            discovered=bool(command)
            configured=bool(explicit or command)
            rows.append(BrowserAdapter(name,role,caps,discovered,configured,command,note).as_dict())
        # Python-native Browser Use may exist without a CLI.
        browser_use=importlib.util.find_spec("browser_use") is not None
        rows.append(BrowserAdapter(
            "browser_use","agent_planner",("semantic_browser_agent","task_planning"),
            browser_use,browser_use,None,
            "Optional planning adapter; KRISHNA remains authority and Playwright remains canonical execution.",
        ).as_dict())
        cereon_endpoint=str(os.getenv("KRISHNA_CEREON_BROWSER_ENDPOINT","")).strip()
        rows.append(BrowserAdapter(
            "cereon_browser_operator","real_browser_extension",
            ("real_logged_in_browser","cdp","console","network","mcp"),
            bool(cereon_endpoint),bool(cereon_endpoint),cereon_endpoint or None,
            "Optional dedicated automation-tab extension endpoint; never touches normal tabs by default.",
        ).as_dict())
        vision_cmd=str(os.getenv("KRISHNA_BROWSER_VISION_RECOVERY_CMD","")).strip()
        rows.append(BrowserAdapter(
            "vision_recovery_bridge","vision_recovery",("screenshot","candidate_selector"),
            bool(vision_cmd),bool(vision_cmd),vision_cmd or None,
            "Configured vision recovery output is untrusted candidate evidence.",
        ).as_dict())
        return {
            "canonical":"playwright",
            "policy":"one Garudanetra fabric; optional adapters are capability providers, never competing authorities",
            "adapters":rows,
            "configured":[x["name"] for x in rows if x["configured"]],
            "discovered":[x["name"] for x in rows if x["discovered"]],
        }

    def command(self,name:str)->str|None:
        wanted=str(name or "").strip().lower()
        status=self.status()
        for row in status["adapters"]:
            if row["name"]==wanted:return row.get("command")
        return None


class GarudanetraBrowserFabric:
    """Canonical browser/computer fabric for KRISHNA.

    The fabric owns live Garudanetra sessions and shares one inspector boundary with
    UI Guardian and Developer verification.  It intentionally does not auto-install,
    auto-enable or silently fall back to third-party browser agents.
    """

    def __init__(self,runtime_root:str|Path,inspector=None,on_closed=None,headless=True,timeout_ms=15000):
        self.runtime_root=Path(runtime_root).resolve()
        self.adapters=BrowserAdapterRegistry(self.runtime_root)
        recovery=BrowserRecoveryAdapter(
            harness_command=self.adapters.command("browser_harness"),
            vision_command=self.adapters.command("vision_recovery_bridge"),
        )
        self.inspector=inspector or BrowserOperator(headless=headless,timeout_ms=timeout_ms)
        self.sessions=GarudanetraSessionManager(
            self.runtime_root,headless=headless,timeout_ms=timeout_ms,
            on_closed=on_closed,recovery=recovery,
        )

    def status(self)->dict:
        sessions=self.sessions.status()
        return {
            "owner":"garudanetra-browser-fabric",
            "canonical_engine":"playwright",
            "sessions":sessions,
            "adapters":self.adapters.status(),
            "capabilities":[
                "private_sessions","task_memory","persistent_workspace",
                "semantic_snapshot_refs","self_healing_recovery","cdp_screencast",
                "owner_takeover","recording","bounded_replay","console_network_evidence",
                "ui_guardian","development_verification","candidate_skill_learning","privacy_probe",
            ],
        }

    def create(self,*args,**kwargs):return self.sessions.create(*args,**kwargs)
    def command(self,*args,**kwargs):return self.sessions.command(*args,**kwargs)
    def frame(self,*args,**kwargs):return self.sessions.frame(*args,**kwargs)
    def frame_info(self,*args,**kwargs):return self.sessions.frame_info(*args,**kwargs)
    def semantic_snapshot(self,*args,**kwargs):return self.sessions.semantic_snapshot(*args,**kwargs)
    def recording(self,*args,**kwargs):return self.sessions.recording(*args,**kwargs)
    def replay(self,*args,**kwargs):return self.sessions.replay(*args,**kwargs)
    def close_all(self,*args,**kwargs):return self.sessions.close_all(*args,**kwargs)

    def inspect(self,*args,**kwargs):
        return self.inspector.inspect(*args,**kwargs)

    def privacy_probe(self,*args,**kwargs):
        return self.inspector.privacy_probe(*args,**kwargs)

    def exhaustive_clickthrough(self,*args,**kwargs):
        return self.inspector.exhaustive_clickthrough(*args,**kwargs)
