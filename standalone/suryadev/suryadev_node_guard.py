"""Optional SURYADEV local crash guardian; belongs to the SAME portable app.

Only supervises the child process that it spawned and owns. Stops after a
bounded number of unexpected exits. Never enumerates/kills OS processes,
modifies source approvals, bypasses hardware protection or touches KRISHNA.
"""
from __future__ import annotations

from collections import deque
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from suryadev_liveops import atomic_json

SCHEMA="suryadev.node-guard.v1"
MAX_FAILURES=3
WINDOW_SECONDS=3600
MIN_RESTART_SECONDS=5
FILE="node-guard-status.json"


class NodeGuard:
    def __init__(self, app_dir, data_root, *, model="collector", adaptive=False,
                 continuous=False, port=8772, runner=None, clock=time.time,
                 sleeper=time.sleep):
        self.app=Path(app_dir).expanduser().resolve()
        self.root=Path(data_root).expanduser().resolve()
        if not (self.app/"start-node.py").is_file():
            raise ValueError("SURYADEV executable entrypoint is missing")
        if not 1024 <= port <= 65535:
            raise ValueError("Invalid dashboard port")
        self.model=model
        self.adaptive=adaptive
        self.continuous=continuous
        self.port=port
        self.runner=runner or subprocess.Popen
        self.clock=clock
        self.sleep=sleeper
        self.failures=deque()
        self.stop_requested=False
        self.child=None
        self.attempts=0

    def _record(self, state, **extra):
        atomic_json(self.root,FILE,{"schema":SCHEMA,"state":state,
                                   "at":float(self.clock()),
                                   "crash_count_in_window":len(self.failures),
                                   "launches":self.attempts,
                                   "child_pid":getattr(self.child,"pid",None),
                                   "owner_spawned_only":True,
                                   "no_unrelated_process_termination":True,
                                   **extra})

    def request_stop(self, *_):
        self.stop_requested=True
        # No PID scanning. Interrupt only our own spawned child.
        if self.child is not None and self.child.poll() is None:
            try:
                if os.name == "nt":
                    self.child.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    # Session owns only the guardian's children. Signal the
                    # group so the dashboard and its managed learner can
                    # release SQLite locks and checkpoints gracefully.
                    os.killpg(self.child.pid, signal.SIGINT)
            except (OSError,ValueError,AttributeError):
                pass

    def run(self):
        self.root.mkdir(parents=True,exist_ok=True)
        self._record("initializing")
        args=[sys.executable,str(self.app/"start-node.py"),
              "--data",str(self.root),"--model",self.model,
              "--port",str(self.port)]
        if self.adaptive:
            args.append("--adaptive-fleet")
        if self.continuous:
            args.append("--continuous")
        flags=getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0) if os.name=="nt" else 0
        while not self.stop_requested:
            now=float(self.clock())
            while self.failures and now-self.failures[0] > WINDOW_SECONDS:
                self.failures.popleft()
            if len(self.failures)>=MAX_FAILURES:
                self._record("quarantined_crash_loop",
                             reason="Max three unexpected exits in a rolling hour")
                return 3
            try:
                self.child=self.runner(args,cwd=str(self.app),shell=False,
                                       creationflags=flags,
                                       start_new_session=(os.name != "nt"))
            except (OSError,ValueError) as exc:
                self.failures.append(float(self.clock()))
                self._record("failed_to_launch",
                             error=type(exc).__name__+": "+str(exc)[:160])
                if not self.stop_requested:
                    self.sleep(MIN_RESTART_SECONDS)
                continue
            self.attempts+=1
            self._record("owned_child_running")
            try:
                code=self.child.wait()
            except KeyboardInterrupt:
                self.request_stop()
                self._record("stopping_by_operator")
                return 0
            if self.stop_requested:
                self._record("stopping_by_operator")
                return 0
            if code == 0:
                self._record("stopped_normally",exit_code=0)
                return 0
            self.failures.append(float(self.clock()))
            self._record("unexpected_exit",exit_code=code)
            if len(self.failures) >= MAX_FAILURES:
                self._record("quarantined_crash_loop",
                             reason="Max three unexpected exits in a rolling hour")
                return 3
            self.sleep(MIN_RESTART_SECONDS)
        self._record("stopping_by_operator")
        return 0


def main(argv=None):
    parser=argparse.ArgumentParser(description="SURYDEV local bounded restart guardian")
    parser.add_argument("--data",type=Path,required=True)
    parser.add_argument("--model",default="collector",
                        choices=("collector","auto","qwen3.5:2b","qwen3.5:4b",
                                 "qwen3.5:9b","gemma3:4b"))
    parser.add_argument("--port",type=int,default=8772)
    parser.add_argument("--adaptive-fleet",action="store_true")
    parser.add_argument("--continuous",action="store_true")
    args=parser.parse_args(argv)
    owner=NodeGuard(Path(__file__).resolve().parent,args.data,model=args.model,
                    port=args.port,adaptive=args.adaptive_fleet,
                    continuous=args.continuous)
    signal.signal(signal.SIGINT,owner.request_stop)
    if hasattr(signal,"SIGTERM"):
        signal.signal(signal.SIGTERM,owner.request_stop)
    return owner.run()


if __name__=="__main__":
    raise SystemExit(main())
