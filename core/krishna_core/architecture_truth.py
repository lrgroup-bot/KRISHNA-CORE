from __future__ import annotations

"""Canonical KRISHNA architecture/source-of-truth audit.

This module is deliberately descriptive. It does not delete duplicates or mark
heuristic orphan candidates as dead code. It gives KRISHNA/Sudarshan a single
machine-readable report that separates canonical source, legacy snapshots,
requirements evidence, duplicate implementations and possible unreferenced
modules.
"""

from collections import Counter, defaultdict
from pathlib import Path
import ast
import hashlib
import json
import time


class ArchitectureTruthAudit:
    VERSION = "architecture-truth-v1"

    LEGACY_ROOTS = (
        "GARUDANETRA_SOURCE",
        "GARUDANETRA_IMPLEMENTATION",
        "KRISHNA_AGI_V1_IMPLEMENTED",
    )

    CANONICAL_ROOTS = (
        "core/krishna_core",
        "core/requirements",
        "core/tests",
        "mobile_v3",
        "scripts",
        "docs",
        ".github/workflows",
    )

    CLASSIFIED_NON_ENTRY_MODULES = {
        "autonomy_loop": "superseded by autonomy_supervisor; retained for historical compatibility",
        "avatar_manifest": "superseded by avatar_asset_pipeline/avatar_production",
        "garudanetra": "legacy compatibility module; browser_fabric is canonical authority",
        "gnn_trainer": "optional experimental local-training adapter; no production training claim",
        "intelligence_gateway": "superseded by Orchestrator plus canonical router/action authority",
        "remote_runtime": "superseded by remote_access plus pairing/permission runtime",
        "runtime_deployer": "utility superseded by DEPLOY_KRISHNA_ONCE.ps1 plus runtime_integrity",
        "runtime_readiness": "superseded by runtime_integrity and runtime acceptance",
        "voice_providers": "superseded by native_voice provider stack",
        "voice_runtime": "superseded by native_voice provider stack",
        "windows_remote_manager": "optional authorization facade; requires an explicit WinRM transport adapter",
        "workers": "superseded by worker_fabric",
    }

    STATUS_VALUES = {
        "VERIFIED",
        "IMPLEMENTED_NOT_VERIFIED",
        "PARTIAL",
        "MISSING",
        "ROADMAP",
        "SUPERSEDED",
        "HARDWARE_UNVERIFIED",
    }

    def __init__(self, repo_root: str | Path):
        self.root = Path(repo_root).resolve()

    @staticmethod
    def _sha(path: Path):
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _files(self, rel_root: str, suffix=None):
        root = self.root / rel_root
        if not root.exists():
            return []
        rows = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or ".pytest_cache" in path.parts:
                continue
            if path.suffix.lower() in {".pyc", ".pyo"}:
                continue
            if suffix and path.suffix.lower() != suffix:
                continue
            rows.append(path)
        return rows

    def _relative(self, path: Path):
        return path.resolve().relative_to(self.root).as_posix()

    def _requirements(self):
        path = self.root / "core" / "requirements" / "krishna_chat_requirements.json"
        if not path.is_file():
            return {
                "present": False,
                "version": None,
                "status_counts": {},
                "evidence_missing": [],
                "implementation_index": [],
            }
        data = json.loads(path.read_text(encoding="utf-8"))
        index = list(data.get("implementation_index") or [])
        missing = []
        status_counts = Counter()
        for item in index:
            status = str(item.get("status") or "MISSING")
            status_counts[status] += 1
            for rel in item.get("evidence") or []:
                if not (self.root / rel).exists():
                    missing.append({"id": item.get("id"), "path": rel})
        return {
            "present": True,
            "version": data.get("version"),
            "schema": data.get("schema"),
            "groups": len(data.get("groups") or []),
            "status_counts": dict(sorted(status_counts.items())),
            "invalid_statuses": sorted(
                {str(x.get("status")) for x in index if str(x.get("status")) not in self.STATUS_VALUES}
            ),
            "evidence_missing": missing,
            "implementation_index": index,
        }

    def _duplicate_inventory(self):
        paths = []
        for rel in self.CANONICAL_ROOTS + self.LEGACY_ROOTS:
            paths.extend(self._files(rel))
        by_name = defaultdict(list)
        by_hash = defaultdict(list)
        for path in paths:
            rel = self._relative(path)
            if path.name.lower() != "__init__.py":
                by_name[path.name.lower()].append(rel)
            try:
                by_hash[self._sha(path)].append(rel)
            except OSError:
                pass
        duplicate_names = [
            {"name": name, "paths": sorted(rows)}
            for name, rows in by_name.items()
            if len(rows) > 1
        ]
        duplicate_content = [
            {"sha256": digest, "paths": sorted(rows)}
            for digest, rows in by_hash.items()
            if len(rows) > 1
        ]
        duplicate_names.sort(key=lambda x: (-len(x["paths"]), x["name"]))
        duplicate_content.sort(key=lambda x: (-len(x["paths"]), x["sha256"]))
        return {
            "same_basename": duplicate_names,
            "identical_content": duplicate_content,
            "policy": (
                "duplicates are evidence for review only; legacy/snapshot copies never "
                "override canonical source and are not automatically deleted"
            ),
        }

    @staticmethod
    def _imported_local_modules(path: Path):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            return set()
        out = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level and node.module:
                    out.add(node.module.split(".", 1)[0])
                elif node.module and node.module.startswith("krishna_core."):
                    out.add(node.module.split(".", 1)[1].split(".", 1)[0])
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("krishna_core."):
                        out.add(alias.name.split(".", 1)[1].split(".", 1)[0])
        return out

    def _orphan_candidates(self):
        core = self.root / "core" / "krishna_core"
        if not core.is_dir():
            return []
        modules = {
            p.stem: p
            for p in core.glob("*.py")
            if p.name != "__init__.py"
        }
        referenced = set()
        scan_roots = [
            self.root / "core" / "krishna_core",
            self.root / "core" / "tests",
        ]
        for root in scan_roots:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                referenced.update(self._imported_local_modules(path))
        entry_allow = {
            "server",
            "command_line",
            "krishna_protocol",
        }
        out = []
        for name, path in sorted(modules.items()):
            if name in referenced or name in entry_allow or name in self.CLASSIFIED_NON_ENTRY_MODULES:
                continue
            out.append(
                {
                    "module": name,
                    "path": self._relative(path),
                    "classification": "review_candidate_only",
                    "reason": "no static local Python import found; dynamic/action registration may still make it reachable",
                }
            )
        return out

    def _classified_non_entry_modules(self):
        rows = []
        core = self.root / "core" / "krishna_core"
        for name, reason in sorted(self.CLASSIFIED_NON_ENTRY_MODULES.items()):
            path = core / f"{name}.py"
            if not path.is_file():
                continue
            rows.append({
                "module": name,
                "path": self._relative(path),
                "classification": "known_non_entry_or_superseded",
                "reason": reason,
            })
        return rows

    def _source_tree_drift(self):
        path = self.root / "KRISHNA_SOURCE_TREE.txt"
        actual = {
            self._relative(p).replace("/", "\\")
            for p in self._files("core/krishna_core", suffix=".py")
        }
        if not path.is_file():
            return {
                "artifact": "KRISHNA_SOURCE_TREE.txt",
                "present": False,
                "missing_current_modules": sorted(actual),
                "stale_entries": [],
            }
        recorded = {
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip()
        }
        recorded_core = {x for x in recorded if x.lower().startswith("core\\krishna_core\\")}
        recorded_modules = {x for x in recorded_core if x.lower().endswith(".py")}
        return {
            "artifact": "KRISHNA_SOURCE_TREE.txt",
            "present": True,
            "missing_current_modules": sorted(actual - recorded_modules),
            "stale_entries": sorted(recorded_modules - actual),
            "canonical": False,
            "policy": "generated/source-tree snapshots are advisory; requirements + current source + runtime acceptance are authoritative",
        }

    def _legacy(self):
        rows = []
        for rel in self.LEGACY_ROOTS:
            root = self.root / rel
            if not root.exists():
                continue
            rows.append(
                {
                    "root": rel,
                    "files": sum(1 for p in root.rglob("*") if p.is_file()),
                    "classification": "SUPERSEDED_OR_COMPATIBILITY_REVIEW",
                    "canonical": False,
                }
            )
        return rows

    def scan(self):
        requirements = self._requirements()
        duplicates = self._duplicate_inventory()
        source_tree = self._source_tree_drift()
        orphans = self._orphan_candidates()
        report = {
            "component": "KRISHNA Architecture Truth Audit",
            "version": self.VERSION,
            "repo_root": str(self.root),
            "generated_at": time.time(),
            "canonical_roots": list(self.CANONICAL_ROOTS),
            "legacy_roots": self._legacy(),
            "requirements": requirements,
            "duplicates": duplicates,
            "orphan_candidates": orphans,
            "classified_non_entry_modules": self._classified_non_entry_modules(),
            "source_tree_drift": source_tree,
            "summary": {
                "requirements_indexed": len(requirements.get("implementation_index") or []),
                "requirements_missing_evidence": len(requirements.get("evidence_missing") or []),
                "legacy_roots_present": len(self._legacy()),
                "duplicate_basenames": len(duplicates["same_basename"]),
                "identical_content_groups": len(duplicates["identical_content"]),
                "orphan_candidates": len(orphans),
                "classified_non_entry_modules": len(self._classified_non_entry_modules()),
                "source_tree_missing_current_modules": len(source_tree.get("missing_current_modules") or []),
            },
            "authority": [
                "core/requirements/krishna_chat_requirements.json",
                "current canonical source",
                "current tests/CI",
                "runtime acceptance evidence",
                "deployment integrity manifest",
            ],
            "non_authority": [
                "old snapshot folders",
                "stale source-tree listings",
                "historical reports",
                "unmerged/divergent feature branches",
            ],
        }
        return report
