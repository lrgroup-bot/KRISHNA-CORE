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
import os
import threading
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

    GENERATED_DIR_NAMES = frozenset({
        ".git",
        ".gradle",
        ".idea",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "htmlcov",
        "logs",
        "node_modules",
        "state",
        "tmp",
        "venv",
    })
    SCAN_CACHE_SECONDS = 60.0

    def __init__(self, repo_root: str | Path):
        self.root = Path(repo_root).resolve()
        self._scan_lock = threading.RLock()
        self._scan_cache = None
        self._scan_cached_at = 0.0

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
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = sorted(
                d for d in dirnames
                if d.lower() not in self.GENERATED_DIR_NAMES
            )
            base = Path(dirpath)
            for filename in sorted(filenames):
                path = base / filename
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
        by_size = defaultdict(list)
        by_hash = defaultdict(list)
        for path in paths:
            rel = self._relative(path)
            if path.name.lower() != "__init__.py":
                by_name[path.name.lower()].append(rel)
            try:
                by_size[path.stat().st_size].append((path, rel))
            except OSError:
                pass
        # Identical files must have the same size. Hash only size-collision groups
        # instead of every source file; this matters on Windows and slower E: drives.
        for rows in by_size.values():
            if len(rows) < 2:
                continue
            for path, rel in rows:
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

    @staticmethod
    def _scope_redefinitions(tree, rel_path):
        rows = []

        def visit_scope(body, scope):
            seen = defaultdict(list)
            for node in body or []:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    seen[node.name].append(int(getattr(node, "lineno", 0) or 0))
            for name, lines in sorted(seen.items()):
                if len(lines) > 1:
                    rows.append({
                        "path": rel_path,
                        "scope": scope,
                        "name": name,
                        "lines": lines,
                        "kind": "same_scope_python_redefinition",
                    })
            for node in body or []:
                if isinstance(node, ast.ClassDef):
                    visit_scope(node.body, scope + "." + node.name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    visit_scope(node.body, scope + "." + node.name)

        visit_scope(getattr(tree, "body", []), "<module>")
        return rows

    def _merge_integrity(self):
        """Detect merge-time collisions that can silently shadow newer work.

        Repeated names in different scopes are allowed (for example a nested
        Shared Action handler and a public Orchestrator method). Only collisions
        inside the same Python scope, duplicated global registrations, and
        duplicate routes inside the same HTTP handler are reported.
        """
        core = self.root / "core" / "krishna_core"
        redefinitions = []
        parse_errors = []
        for path in sorted(core.glob("*.py")) if core.is_dir() else []:
            try:
                text = path.read_text(encoding="utf-8")
                tree = ast.parse(text)
            except (SyntaxError, UnicodeDecodeError, OSError) as exc:
                parse_errors.append({
                    "path": self._relative(path),
                    "error": f"{type(exc).__name__}: {exc}",
                })
                continue
            redefinitions.extend(self._scope_redefinitions(tree, self._relative(path)))

        def call_key(node):
            if not isinstance(node, ast.Call) or not node.args:
                return None
            arg = node.args[0]
            return arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else None

        registrations = {
            "action_bus": defaultdict(list),
            "agent_runtime": defaultdict(list),
        }
        orchestrator = core / "orchestrator.py"
        if orchestrator.is_file():
            try:
                tree = ast.parse(orchestrator.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    fn = node.func
                    if not isinstance(fn, ast.Attribute) or fn.attr != "register":
                        continue
                    owner = fn.value
                    if not isinstance(owner, ast.Attribute):
                        continue
                    if not isinstance(owner.value, ast.Name) or owner.value.id != "self":
                        continue
                    category = None
                    if owner.attr == "action_bus":
                        category = "action_bus"
                    elif owner.attr == "agent_runtime":
                        category = "agent_runtime"
                    if category:
                        key = call_key(node)
                        if key:
                            registrations[category][key].append(int(getattr(node, "lineno", 0) or 0))
            except (SyntaxError, UnicodeDecodeError, OSError) as exc:
                parse_errors.append({
                    "path": self._relative(orchestrator),
                    "error": f"{type(exc).__name__}: {exc}",
                })

        duplicate_regs = {}
        for category, groups in registrations.items():
            duplicate_regs[category] = [
                {"name": key, "lines": lines}
                for key, lines in sorted(groups.items())
                if len(lines) > 1
            ]

        duplicate_routes = []
        server = core / "server.py"
        if server.is_file():
            try:
                tree = ast.parse(server.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    if node.name not in {"_get", "_post"}:
                        continue
                    variable = "path" if node.name == "_get" else "post_path"
                    found = defaultdict(list)
                    for child in ast.walk(node):
                        if not isinstance(child, ast.Compare) or len(child.ops) != 1:
                            continue
                        if not isinstance(child.left, ast.Name) or child.left.id != variable:
                            continue
                        values = []
                        rhs = child.comparators[0]
                        if isinstance(child.ops[0], ast.Eq) and isinstance(rhs, ast.Constant) and isinstance(rhs.value, str):
                            values = [rhs.value]
                        elif isinstance(child.ops[0], ast.In) and isinstance(rhs, (ast.Tuple, ast.List, ast.Set)):
                            values = [
                                x.value for x in rhs.elts
                                if isinstance(x, ast.Constant) and isinstance(x.value, str)
                            ]
                        for value in values:
                            found[value].append(int(getattr(child, "lineno", 0) or 0))
                    for route, lines in sorted(found.items()):
                        if len(lines) > 1:
                            duplicate_routes.append({
                                "handler": node.name,
                                "route": route,
                                "lines": lines,
                            })
            except (SyntaxError, UnicodeDecodeError, OSError) as exc:
                parse_errors.append({
                    "path": self._relative(server),
                    "error": f"{type(exc).__name__}: {exc}",
                })

        declared_id_specs = (
            ("duplicate_specialist_ids", core / "specialist_registry.py", "Specialist"),
            ("duplicate_rishi_ids", core / "rishi_council.py", "RishiProfile"),
            ("duplicate_3d_provider_ids", core / "three_d_model_router.py", "ThreeDProvider"),
        )
        duplicate_declared_ids = {}
        for result_key, path, constructor in declared_id_specs:
            groups = defaultdict(list)
            if path.is_file():
                try:
                    tree = ast.parse(path.read_text(encoding="utf-8"))
                    for node in ast.walk(tree):
                        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != constructor:
                            continue
                        key = call_key(node)
                        if key:
                            groups[key].append(int(getattr(node, "lineno", 0) or 0))
                except (SyntaxError, UnicodeDecodeError, OSError) as exc:
                    parse_errors.append({
                        "path": self._relative(path),
                        "error": f"{type(exc).__name__}: {exc}",
                    })
            duplicate_declared_ids[result_key] = [
                {"name": key, "lines": lines}
                for key, lines in sorted(groups.items())
                if len(lines) > 1
            ]

        return {
            "same_scope_python_redefinitions": redefinitions,
            "duplicate_action_bus_registrations": duplicate_regs["action_bus"],
            "duplicate_agent_runtime_registrations": duplicate_regs["agent_runtime"],
            "duplicate_http_routes_same_handler": duplicate_routes,
            "duplicate_specialist_ids": duplicate_declared_ids["duplicate_specialist_ids"],
            "duplicate_rishi_ids": duplicate_declared_ids["duplicate_rishi_ids"],
            "duplicate_3d_provider_ids": duplicate_declared_ids["duplicate_3d_provider_ids"],
            "parse_errors": parse_errors,
            "policy": (
                "cross-scope repeated names and GET-vs-POST reuse are legitimate; "
                "same-scope redefinitions and duplicate global registrations are merge hazards"
            ),
        }

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
                    "files": len(self._files(rel)),
                    "classification": "SUPERSEDED_OR_COMPATIBILITY_REVIEW",
                    "canonical": False,
                }
            )
        return rows

    def scan(self, force=False):
        now = time.monotonic()
        with self._scan_lock:
            if (
                not force
                and self._scan_cache is not None
                and now - self._scan_cached_at < self.SCAN_CACHE_SECONDS
            ):
                return self._scan_cache

            requirements = self._requirements()
            duplicates = self._duplicate_inventory()
            merge_integrity = self._merge_integrity()
            source_tree = self._source_tree_drift()
            orphans = self._orphan_candidates()
            legacy = self._legacy()
            classified = self._classified_non_entry_modules()
            report = {
                "component": "KRISHNA Architecture Truth Audit",
                "version": self.VERSION,
                "repo_root": str(self.root),
                "generated_at": time.time(),
                "canonical_roots": list(self.CANONICAL_ROOTS),
                "legacy_roots": legacy,
                "requirements": requirements,
                "duplicates": duplicates,
                "merge_integrity": merge_integrity,
                "orphan_candidates": orphans,
                "classified_non_entry_modules": classified,
                "source_tree_drift": source_tree,
                "summary": {
                    "requirements_indexed": len(requirements.get("implementation_index") or []),
                    "requirements_missing_evidence": len(requirements.get("evidence_missing") or []),
                    "legacy_roots_present": len(legacy),
                    "duplicate_basenames": len(duplicates["same_basename"]),
                    "identical_content_groups": len(duplicates["identical_content"]),
                    "same_scope_python_redefinitions": len(merge_integrity["same_scope_python_redefinitions"]),
                    "duplicate_action_bus_registrations": len(merge_integrity["duplicate_action_bus_registrations"]),
                    "duplicate_agent_runtime_registrations": len(merge_integrity["duplicate_agent_runtime_registrations"]),
                    "duplicate_http_routes_same_handler": len(merge_integrity["duplicate_http_routes_same_handler"]),
                    "duplicate_specialist_ids": len(merge_integrity["duplicate_specialist_ids"]),
                    "duplicate_rishi_ids": len(merge_integrity["duplicate_rishi_ids"]),
                    "duplicate_3d_provider_ids": len(merge_integrity["duplicate_3d_provider_ids"]),
                    "merge_integrity_parse_errors": len(merge_integrity["parse_errors"]),
                    "orphan_candidates": len(orphans),
                    "classified_non_entry_modules": len(classified),
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
            self._scan_cache = report
            self._scan_cached_at = time.monotonic()
            return report
