"""Fail-closed source/module audit for the installed SURYADEV package.

Run with: python -I verify_runtime_package.py --root PATH
The -I flag prevents tests in the source checkout from hiding missing
installed modules via the current working directory or PYTHONPATH.
"""
from __future__ import annotations

import argparse
import ast
import importlib
from pathlib import Path
import sys


REQUIRED_ENTRYPOINTS = (
    "suryadev",
    "suryadev_extras",
    "suryadev_fleet_client",
    "suryadev_plugins",
    "suryadev_rakshak",
    "suryadev_model_router",
    "suryadev_mission_cycle",
    "suryadev_source_authority",
    "suryadev_video_review",
    "suryadev_operator_api",
)
REQUIRED_FRONTEND = (
    "node-console.html", "node-console.css", "node-console.js",
    "dashboard.html",
    "dashboard.js",
    "dashboard.css",
    "dashboard-settings.js",
    "dashboard-settings.css",
    "dashboard-garudanetra.js",
    "dashboard-garudanetra.css",
    "dashboard-books.js",
    "dashboard-books.css",
    "dashboard-video.js",
    "dashboard-video.css",
)
REQUIRED_WORKERS = ("suryadev_r39_worker.py", "suryadev_r39_adapter.py")


def local_import_names(source):
    """Inspect all Python import locations, including lazy function imports."""
    source = Path(source)
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            candidates = (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level:
            candidates = (node.module or "",)
        else:
            continue
        for qualified in candidates:
            name = qualified.split(".", 1)[0]
            if name == "suryadev" or name.startswith("suryadev_"):
                yield name


def missing_runtime_files(root):
    """Do not import/execute code while checking on-disk package completeness."""
    root = Path(root).resolve()
    errors = []
    available = {p.stem for p in root.glob("*.py") if p.is_file()}
    required = set(REQUIRED_ENTRYPOINTS)
    for source in root.glob("*.py"):
        if source.is_file():
            try:
                required.update(local_import_names(source))
            except (OSError, SyntaxError, UnicodeError) as exc:
                errors.append(f"Unreadable installed Python source {source.name}: {exc}")
    for name in sorted(required - available):
        errors.append(f"Missing installed Python module: {name}.py")
    for name in (*REQUIRED_FRONTEND, *REQUIRED_WORKERS):
        if not (root / name).is_file():
            errors.append(f"Missing installed asset: {name}")
    return errors


def verify(root):
    root = Path(root).resolve(strict=True)
    problems = missing_runtime_files(root)
    if problems:
        raise RuntimeError("; ".join(problems))
    # Must be invoked with -I; otherwise source checkout can mask missing files.
    if not sys.flags.isolated:
        raise RuntimeError("Refusing non-isolated import check: launch Python with -I")
    sys.path.insert(0, str(root))
    for name in REQUIRED_ENTRYPOINTS:
        module = importlib.import_module(name)
        location = Path(module.__file__).resolve()
        if location.parent != root:
            raise RuntimeError(f"Module {name} loaded outside installed app: {location}")
    print(f"PASS: SURYADEV runtime package complete and isolated imports resolve inside {root}")


def main():
    parser = argparse.ArgumentParser(description="Audit SURYADEV installed runtime")
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    try:
        verify(args.root)
    except (RuntimeError, ImportError, OSError, ValueError, SyntaxError) as exc:
        print(f"FAIL: installed SURYADEV runtime not verified: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
