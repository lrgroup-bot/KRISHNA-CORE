from __future__ import annotations

from pathlib import Path
from .security import DefensiveSecurityScanner


class ApplicationSecurityLoop:
    """Defensive source-security loop: model -> scan -> reproduce safely -> patch -> retest."""

    def __init__(self):
        self.scanner=DefensiveSecurityScanner()

    def threat_model(self,project_root,entry_points=None,sensitive_assets=None):
        root=Path(project_root).resolve()
        return {
            "root":str(root),
            "entry_points":list(entry_points or []),
            "sensitive_assets":list(sensitive_assets or ["credentials","tokens","user data","deployment keys"]),
            "trust_boundaries":["external input -> application","application -> filesystem","application -> network/provider","worker -> production"],
            "policy":"authorized defensive analysis only",
        }

    def scan(self,paths):return self.scanner.scan_paths(paths)

    def reproduction_plan(self,finding:dict,candidate_root):
        return {
            "finding":dict(finding),
            "candidate_root":str(Path(candidate_root).resolve()),
            "live_target_allowed":False,
            "network_external_target_allowed":False,
            "steps":["create minimal local fixture","execute in candidate/sandbox only","capture evidence","discard fixture"],
            "requires_verification":True,
        }

    def remediation_gate(self,before:dict,after:dict,regression:dict):
        before_count=len(before.get("findings") or [])
        after_count=len(after.get("findings") or [])
        passed=after_count<before_count and bool(regression.get("passed"))
        return {"passed":passed,"before_findings":before_count,"after_findings":after_count,"regression":regression}
