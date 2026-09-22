from __future__ import annotations

import argparse
import ast
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core" / "krishna_core"

ENTRYPOINT_MODULES = {
    "__init__", "server", "orchestrator", "run_core", "command_line",
}

COMPATIBILITY_ROOTS = (
    "GARUDANETRA_SOURCE/core/krishna_core",
    "GARUDANETRA_IMPLEMENTATION/GARUDANETRA_INSTALL/payload/core/krishna_core",
    "KRISHNA_AGI_V1_IMPLEMENTED/core/krishna_core",
)

def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def python_modules() -> dict[str, Path]:
    return {p.stem: p for p in CORE.glob("*.py") if p.is_file()}

def imports_for(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level and node.module:
                out.add(node.module.split(".")[0])
            elif node.module and node.module.startswith("krishna_core."):
                out.add(node.module.split(".", 1)[1].split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith("krishna_core."):
                    out.add(name.split(".", 1)[1].split(".")[0])
    return out

def symbol_index(paths: list[Path]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                index[node.name].append(rel(path))
    return {k: sorted(v) for k, v in index.items() if len(v) > 1 and not k.startswith("_")}

def text_reference_count(module: str) -> int:
    needle = module
    count = 0
    for base in (ROOT / "core", ROOT / "scripts", ROOT / "tests", ROOT / ".github"):
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in {".py", ".ps1", ".yml", ".yaml", ".json", ".html", ".js", ".java", ".md"}:
                continue
            if p.parent == CORE and p.stem == module:
                continue
            try:
                if needle in p.read_text(encoding="utf-8-sig", errors="ignore"):
                    count += 1
            except Exception:
                pass
    return count

def compatibility_copies() -> list[dict]:
    canonical = {p.name: p for p in CORE.glob("*.py")}
    rows = []
    for root_name in COMPATIBILITY_ROOTS:
        root = ROOT / root_name
        if not root.exists():
            continue
        for copy in root.glob("*.py"):
            source = canonical.get(copy.name)
            rows.append({
                "copy": rel(copy),
                "canonical": rel(source) if source else None,
                "same_content": bool(source and digest(copy) == digest(source)),
                "status": "identical_copy" if source and digest(copy) == digest(source) else ("drifted_copy" if source else "copy_only"),
            })
    return sorted(rows, key=lambda x: x["copy"])

def stale_source_tree() -> dict:
    snapshot = ROOT / "KRISHNA_SOURCE_TREE.txt"
    actual = sorted(
        rel(p) for p in ROOT.rglob("*")
        if p.is_file()
        and ".git/" not in rel(p)
        and "__pycache__/" not in rel(p)
        and "/.pytest_cache/" not in ("/" + rel(p))
    )
    if not snapshot.exists():
        return {"snapshot_present": False, "missing_from_snapshot": actual, "snapshot_only": []}
    listed = sorted({line.strip().replace("\\", "/") for line in snapshot.read_text(encoding="utf-8-sig").splitlines() if line.strip()})
    return {
        "snapshot_present": True,
        "missing_from_snapshot": sorted(set(actual) - set(listed)),
        "snapshot_only": sorted(set(listed) - set(actual)),
    }

def audit() -> dict:
    modules = python_modules()
    inbound: dict[str, set[str]] = {m: set() for m in modules}
    imports: dict[str, list[str]] = {}
    for name, path in modules.items():
        deps = {d for d in imports_for(path) if d in modules and d != name}
        imports[name] = sorted(deps)
        for dep in deps:
            inbound[dep].add(name)

    orphan_candidates = []
    for name, path in sorted(modules.items()):
        refs = text_reference_count(name)
        if name not in ENTRYPOINT_MODULES and not inbound[name] and refs == 0:
            orphan_candidates.append({
                "module": name,
                "path": rel(path),
                "reason": "no static inbound core import and no repository text reference",
                "deletion_safe": False,
            })

    same_hash: dict[str, list[str]] = defaultdict(list)
    for p in ROOT.rglob("*.py"):
        if p.is_file() and "__pycache__" not in p.parts:
            same_hash[digest(p)].append(rel(p))
    exact_duplicates = [sorted(v) for v in same_hash.values() if len(v) > 1]

    return {
        "schema": "krishna.architecture-audit.v1",
        "canonical_core": "core/krishna_core",
        "module_count": len(modules),
        "imports": imports,
        "orphan_candidates": orphan_candidates,
        "duplicate_public_symbols": symbol_index(list(modules.values())),
        "exact_duplicate_python_files": sorted(exact_duplicates, key=lambda x: x[0]),
        "compatibility_copies": compatibility_copies(),
        "source_tree_snapshot": stale_source_tree(),
        "policy": {
            "orphan_is_candidate_only": True,
            "delete_requires_dynamic_packaging_runtime_check": True,
            "compatibility_copy_is_not_authority": True,
        },
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Audit KRISHNA duplicate, compatibility and unused-code candidates.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args()
    report = audit()
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    if args.json or not args.out:
        print(text)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
