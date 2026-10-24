"""Portable SURYADEV source installer for Windows/Linux/macOS.

Installs Python and static dashboard assets, without installing Ollama,
creating a service, pairing KRISHNA, or reading/modifying any learning ledger.
Requires a full Git checkout for the canonical R39 worker/adapter.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def install(source: Path, destination: Path, *, update=False, tests=True):
    source = source.resolve()
    destination = destination.expanduser().resolve()
    if destination == source or source in destination.parents:
        raise ValueError("Install directory must be separate from the source checkout")
    repo = source.parent.parent
    observer = repo / "core" / "suryadev_worker.py"
    adapter = repo / "scripts" / "SURYDEV_VIDEO_LEARNING_ADAPTER.py"
    for candidate in (observer, adapter, source/"verify_runtime_package.py",
                      source/"suryadev_extras.py", source/"dashboard.html"):
        if not candidate.is_file():
            raise FileNotFoundError("Full KRISHNA-CORE checkout is required: " + str(candidate))
    marker = destination/"portable-node-install.json"
    if destination.exists() and any(destination.iterdir()):
        if not update or not marker.is_file():
            raise ValueError("Install directory already has files; only a marked portable "
                             "installation can be updated with --update")
        state = json.loads(marker.read_text(encoding="utf-8"))
        if state.get("schema") != "suryadev.portable-node-install.v1":
            raise ValueError("Invalid portable installation marker")
    if tests:
        print("Running bundled source tests BEFORE changing install files", flush=True)
        test_gate = source / "install_test_gate.py"
        result = subprocess.run([sys.executable, str(test_gate), "--source", str(source)])
        if result.returncode:
            raise RuntimeError("Source tests failed: installation has not begun")
    # Copy only top-level code and visual assets; never copy caches, tests,
    # hidden files, local credentials, SQLite databases, or study evidence.
    assets = sorted(x for x in source.iterdir() if x.is_file() and
                    (x.suffix.lower() in {".py", ".html", ".css", ".js", ".ps1"}
                     or x.name.endswith(".example.json") or x.name == "README.md"))
    destination.mkdir(parents=True, exist_ok=True)
    for asset in assets:
        shutil.copy2(asset, destination / asset.name)
    shutil.copy2(observer, destination / "suryadev_r39_worker.py")
    shutil.copy2(adapter, destination / "suryadev_r39_adapter.py")
    result = subprocess.run([sys.executable, "-I",
                             str(destination/"verify_runtime_package.py"),
                             "--root", str(destination)])
    if result.returncode:
        raise RuntimeError("Installed runtime verification failed. Do not start this node.")
    marker.write_text(json.dumps({"schema":"suryadev.portable-node-install.v1",
                                  "source":str(source),"release_file_count":len(assets)+2},
                                 indent=2)+"\n",encoding="utf-8")
    return destination


def main(argv=None):
    ap = argparse.ArgumentParser(description="Install SURYADEV on any Python-compatible CPU")
    ap.add_argument("--install-dir", type=Path, required=True)
    ap.add_argument("--update", action="store_true",
                    help="Update an existing marked portable installation, only while stopped")
    args = ap.parse_args(argv)
    if sys.version_info < (3, 10):
        ap.error("Python 3.10+ required")
    root = Path(__file__).resolve().parent
    output = install(root, args.install_dir, update=args.update)
    print("SURYADEV installed to:", output)
    print("Install psutil for workload monitoring; Ollama is OPTIONAL.")
    print("Run: " + sys.executable + " " + str(output/"start-node.py")
          + " --model collector")


if __name__ == "__main__":
    main()
