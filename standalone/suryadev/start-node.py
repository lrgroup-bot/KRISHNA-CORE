"""Portable SURYADEV node launcher: Windows, Linux and macOS, no paid services.

The default role is evidence collection only; Ollama is not required.
Fresh workspace data is isolated. Existing evidence is NEVER deleted.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
from datetime import datetime, timezone


MODELS = ("collector", "auto", "qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b", "gemma3:4b")
MARKER_SCHEMA = "suryadev.fresh-workspace.v1"


def prepare(data: Path, *, model: str, previous: Path | None = None,
            new_session: bool = False, adaptive_fleet: bool = False,
            continuous: bool = False, fast_books: bool | None = None) -> Path:
    """Initialize or reopen a fresh study ledger without removing prior files."""
    if model not in MODELS:
        raise ValueError("Unsupported learning mode")
    raw_data = data.expanduser().absolute()
    if raw_data.is_symlink():
        raise ValueError("Fresh data directory must not be a symbolic link")
    data = raw_data.resolve()
    if new_session:
        data = data.with_name(data.name + "-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    if previous is not None:
        previous = previous.expanduser().resolve()
        if not previous.is_dir():
            raise ValueError("Previous learning data not found: " + str(previous))
        if data == previous or previous in data.parents:
            raise ValueError("New workspace must not be within the old evidence directory")
    if data.exists() and not data.is_dir():
        raise ValueError("Data location is not a directory")
    if data.exists() and data.is_symlink():
        raise ValueError("Fresh data directory must not be a symbolic link")
    data.mkdir(parents=True, exist_ok=True)
    marker = data / "fresh-workspace.json"
    if marker.exists():
        state = json.loads(marker.read_text(encoding="utf-8"))
        if state.get("schema") != MARKER_SCHEMA:
            raise ValueError("Existing fresh workspace marker is invalid")
    else:
        if any(data.iterdir()):
            raise ValueError("Nonempty unmarked data directory; choose another location")
        state = {
            "schema": MARKER_SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
            "active_task_limit": 3, "auto_start": True,
            "note": "Dedicated node evidence; local Ollama is optional.",
        }
    if previous is not None and "previous_learning_preserved_at" not in state:
        state["previous_learning_preserved_at"] = str(previous)
    # Fleet mode is deliberately opt-in for the first release. Existing laptop
    # installations retain their legacy three-task safety contract.
    if adaptive_fleet:
        state["node_profile"] = "fleet_adaptive"
        state["active_task_limit"] = 125  # Upper cap; resource admission always wins.
    if continuous:
        state["mission_rest_policy"] = "continuous"  # Never disables 85% safety.
    # Explicit mode selection may change the inference backend, not study evidence.
    state["trial_model"] = model
    if fast_books is not None:
        if type(fast_books) is not bool:
            raise ValueError("fast_books must be a boolean")
        state["fast_books"] = fast_books
    temp = data / (".fresh-workspace-" + secrets.token_hex(8) + ".tmp")
    try:
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        os.replace(temp, marker)
    finally:
        temp.unlink(missing_ok=True)
    return data


def available_port(port: int) -> bool:
    if not 1024 <= port <= 65535:
        raise ValueError("Port must be between 1024 and 65535")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description="Portable SURYADEV CPU/laptop collector node")
    ap.add_argument("--data", type=Path, default=Path.home() / "SURYADEV-NODE-DATA")
    ap.add_argument("--previous-data", type=Path, default=None)
    ap.add_argument("--model", choices=MODELS, default="collector",
                    help="collector=NO Ollama; auto=installed lightweight model only with safe headroom")
    ap.add_argument("--port", type=int, default=8772)
    ap.add_argument("--new-session", action="store_true")
    ap.add_argument("--approved-trial", action="store_true",
                    help="Run the previously owner-approved fixed YouTube/book trial")
    ap.add_argument("--standalone-test", action="store_true",
                    help="Disable KRISHNA/Core mission pairing for independent local acceptance")
    ap.add_argument("--auto-approved-videos", action="store_true",
                    help="Automatically observe only exact approved video URLs under hardware guard")
    ap.add_argument("--adaptive-fleet", action="store_true",
                    help="Enable resource-measured fleet capacity instead of legacy three-task ceiling")
    ap.add_argument("--continuous", action="store_true",
                    help="Rollover six-hour mission accounting without forced rest; safety/source pauses remain")
    ap.add_argument("--fast-books", action=argparse.BooleanOptionalAction, default=None,
                    help="Use compact up-to-40-line sequential book checkpoints; no skipped source lines, same local 2B model")
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--video-target",type=int,choices=range(1,6),default=None,
                    help="Trial: select at most 5 distinct previously unattempted approved videos")
    ap.add_argument("--website-target",type=int,choices=range(1,6),default=None,
                    help="Trial: at most 5 concurrent approved website tasks, hardware permitting")
    ap.add_argument("--pdf-target",type=int,choices=range(1,11),default=None,
                    help="Trial: at most 10 concurrent PDF tasks, hardware permitting")
    ap.add_argument("--book-target",type=int,choices=range(1,6),default=None,
                    help="Trial: at most 5 concurrent book-reading tasks, hardware permitting")
    ap.add_argument("--max-parallel",type=int,default=None,
                    help="Optional TOTAL cap (1..125); only reduces measured concurrency")
    args = ap.parse_args(argv)
    if args.max_parallel is not None and not 1<=args.max_parallel<=125:
        ap.error("--max-parallel must be 1..125")
    if not args.prepare_only and not available_port(args.port):
        ap.error("Dashboard port is in use; stop the previous dashboard first")
    data = prepare(args.data, model=args.model, previous=args.previous_data,
                   new_session=args.new_session, adaptive_fleet=args.adaptive_fleet,
                   continuous=args.continuous, fast_books=args.fast_books)
    print("SURYADEV data:", data, flush=True)
    marker = json.loads((data / "fresh-workspace.json").read_text(encoding="utf-8"))
    fleet_profile = marker.get("node_profile") == "fleet_adaptive"
    active_cap = 125 if fleet_profile else 3
    print("Node mode:", args.model, "| admission cap:", active_cap,
          "| resource measured, never guaranteed | 85% safety guard", flush=True)
    print("Previous evidence remains untouched; KRISHNA pairing is not auto-provisioned.",flush=True)
    if args.prepare_only:
        return 0
    env = os.environ.copy()
    env["SURYADEV_MAX_PARALLEL"] = str(min(active_cap,args.max_parallel or active_cap))
    for attr, variable in (
      ("video_target","SURYADEV_TRIAL_VIDEO_COUNT"),
      ("website_target","SURYADEV_TRIAL_WEBSITE_TARGET"),
      ("pdf_target","SURYADEV_TRIAL_PDF_TARGET"),
      ("book_target","SURYADEV_TRIAL_BOOK_TARGET")):
        value=getattr(args,attr)
        if value is not None:
            env[variable]=str(value)
        else:
            # Old shell environment must not silently activate a trial.
            env.pop(variable,None)
    if args.video_target is not None:
        print("Approved-video target:",args.video_target,
              "| one-time exact-URL selection; no replay or invented approvals",flush=True)
    if any(getattr(args,n) is not None for n in
           ("website_target","pdf_target","book_target")):
        print("Other lane targets: websites",args.website_target,
              "| PDFs",args.pdf_target,"| books",args.book_target,
              "| measured admission may be lower",flush=True)
    # The approved public sources are not fetched implicitly on all fleet nodes.
    env["SURYADEV_BOOK_FAST"] = "1" if marker.get("fast_books") is True else "0"
    if marker.get("fast_books") is True:
        print("FAST BOOKS: compact up-to-40-line batches; CPU guard and journal integrity unchanged.",
              flush=True)
    env["SURYADEV_LEARNING_TRIAL"] = "1" if args.approved_trial else "0"
    env["SURYADEV_AUTO_APPROVED_VIDEOS"] = "1" if args.auto_approved_videos else "0"
    env["SURYADEV_STANDALONE_TEST"] = "1" if args.standalone_test else "0"
    if args.standalone_test:
        print("STANDALONE TEST: KRISHNA pairing, mission relay, fleet polling and handoff disabled.",flush=True)
    entry = Path(__file__).resolve().with_name("suryadev_extras.py")
    return subprocess.call([sys.executable, str(entry), "--data", str(data),
                            "dashboard", "--port", str(args.port)],
                           cwd=str(entry.parent), env=env)


if __name__ == "__main__":
    raise SystemExit(main())
