"""Frozen Windows entrypoint for the complete local SURYADEV AI Learner.

The original standalone app remains source-backed under the bundled app/
directory. Re-invocations by the supervised worker must use this executable
as the interpreter, so route ONLY scripts physically inside our bundled app.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import runpy
import sys


def _base() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()


def _app() -> Path:
    return _base() / "app"


def _install_runtime() -> Path:
    app = _app().resolve()
    if not (app / "start-node.py").is_file() or not (
            app / "suryadev_extras.py").is_file() or not (
            app / "dashboard.html").is_file():
        raise RuntimeError("Incomplete SURYADEV package: bundled app files missing")
    if str(app) not in sys.path:
        sys.path.insert(0, str(app))
    from suryadev_setup import tesseract_path
    ocr = tesseract_path()
    if ocr:
        os.environ["PATH"] = str(Path(ocr).parent) + os.pathsep + os.environ.get("PATH", "")
    bundled_browsers = _base() / "playwright-browsers"
    if bundled_browsers.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled_browsers)
    return app


def _run_script(script: Path, arguments: list[str], app: Path) -> None:
    script = script.expanduser().resolve()
    if script.parent != app or not script.is_file() or script.suffix != ".py":
        raise ValueError("Refusing to launch an executable script outside bundled SURYADEV")
    sys.argv = [str(script), *arguments]
    runpy.run_path(str(script), run_name="__main__")


def main(argv=None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    app = _install_runtime()
    # PyInstaller's sys.executable refers to THIS exe. The normal app invokes
    # its children as: [sys.executable, '-u', script, ...]. Retain that API
    # without spawning a second Python installation or arbitrary scripts.
    if arguments and arguments[0] in ("-u", "-I"):
        if len(arguments) < 2:
            raise ValueError("Script path missing from worker invocation")
        _run_script(Path(arguments[1]), arguments[2:], app)
        return 0
    if arguments and arguments[0].endswith(".py"):
        _run_script(Path(arguments[0]), arguments[1:], app)
        return 0

    exe_dir = (Path(sys.executable).resolve().parent
               if getattr(sys, "frozen", False)
               else Path(__file__).resolve().parent)
    default_data = exe_dir / "data"
    if arguments and arguments[0] == "--self-test":
        import json
        import importlib
        from verify_runtime_package import REQUIRED_ENTRYPOINTS, missing_runtime_files
        problems = missing_runtime_files(app)
        if problems:
            raise RuntimeError("; ".join(problems))
        for name in REQUIRED_ENTRYPOINTS:
            importlib.import_module(name)
        # Import the lazy backend's standard-library extensions too; merely
        # finding source files cannot verify a working frozen interpreter.
        import sqlite3
        import ssl
        print(json.dumps({
            "ok": True, "app": str(app),
            "has_ai_learner": (app / "dashboard-ai-learner.js").is_file(),
            "has_reset": (app / "suryadev_learning_reset.py").is_file(),
            "bundled_chromium": (_base() / "playwright-browsers").is_dir(),
            "no_learning_data_read": True,
            "backend_imports_verified": True,
            "sqlite_version": sqlite3.sqlite_version,
            "ssl_version": ssl.OPENSSL_VERSION,
        }, indent=2))
        return 0

    if arguments and arguments[0] == "--reset-learning":
        parser = argparse.ArgumentParser(description="Archive existing learning and reset")
        parser.add_argument("--data", type=Path, default=default_data)
        parser.add_argument("--confirm", default="")
        args = parser.parse_args(arguments[1:])
        from suryadev_learning_reset import archive_and_reset
        import json
        print(json.dumps(archive_and_reset(args.data, confirm=args.confirm), indent=2))
        return 0

    if not arguments:
        # Only begins with a blank plan. No source is invented or authorized.
        arguments = [
            "--data", str(default_data), "--model", "auto",
            "--fast-books", "--adaptive-fleet",
            "--continuous", "--auto-approved-videos", "--website-target", "5",
            "--video-target", "5", "--pdf-target", "10", "--book-target", "5",
            "--max-parallel", "25",
            "--port", "8872",
        ]
        os.environ["SURYADEV_AUTO_SETUP"] = "1"
    elif "--data" not in arguments:
        arguments = ["--data", str(default_data), *arguments]
    _run_script(app / "start-node.py", arguments, app)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print("SURYADEV ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
