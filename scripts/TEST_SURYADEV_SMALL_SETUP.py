"""Real small-EXE LAN install, idempotent retry and frozen UI acceptance.

Only a new explicitly selected test directory is used. Missing model/runtime
installation is NOT claimed: --skip-components is recorded as a test skip.
"""
import argparse
import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from urllib.request import Request, build_opener, ProxyHandler


def run(release, root):
    release, root = release.resolve(), root.resolve()
    if root.exists():
        raise RuntimeError("Choose a new empty installer-test directory")
    manifest = json.loads((release / "SETUP-RELEASE.json").read_text(encoding="utf-8-sig"))
    payload = release / "SURYADEV-Learner-Payload.zip"
    with payload.open("rb") as stream:
        payload_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    if payload_hash != manifest["payload_sha256"]:
        raise RuntimeError("Test payload differs from the setup build")
    requests = []
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            return super().do_GET()
        def log_message(self, *args): pass
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
        functools.partial(Handler, directory=str(release)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    source = "http://127.0.0.1:%d/SURYADEV-Learner-Payload.zip" % server.server_port
    command = [str(release / "SURYADEV-Setup.exe"), "--headless", "--install-dir", str(root),
               "--source", source, "--skip-components"]
    report = {"real_bootstrap_exe": True, "source": "isolated_loopback_LAN_mirror",
              "external_component_installation": "explicitly_skipped_in_integration_test",
              "existing_user_learning_modified": False, "real_krishna_pairing_verified": False}
    opener = build_opener(ProxyHandler({}))
    child = None
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=600)
        if result.returncode != 20:
            raise RuntimeError("Real setup failed: " + str(result.returncode) + result.stderr[-2000:])
        receipt = json.loads((root / "suryadev-install.json").read_text())
        exe = Path(receipt["Exe"])
        if not exe.is_file() or not receipt["ComponentsSkipped"]:
            raise RuntimeError("Incorrect installed receipt")
        data = root / "data"
        prepared = subprocess.run([str(exe), "--data", str(data), "--model", "collector",
            "--adaptive-fleet", "--continuous", "--prepare-only"], capture_output=True,
            text=True, encoding="utf-8", timeout=90)
        if prepared.returncode:
            raise RuntimeError("Installed frozen launcher failed: " + prepared.stderr[-1000:])
        sentinel = data / "existing-learning.receipt"
        sentinel.write_bytes(b"must survive installer retry byte-for-byte")
        before_requests = len(requests)
        again = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=180)
        if again.returncode != 20 or sentinel.read_bytes() != b"must survive installer retry byte-for-byte":
            raise RuntimeError("Installer retry did not preserve the data directory")
        if len(requests) != before_requests:
            raise RuntimeError("Verified package cache was not reused")
        report.update(download_requests=len(requests), verified_cache_reused=True,
                      installed_data_preserved=True, stable_data_directory=True)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0)); port = probe.getsockname()[1]
        log = (release / "integration-dashboard.log").open("w", encoding="utf-8")
        child = subprocess.Popen([str(exe), "--data", str(data), "--model", "collector",
            "--standalone-test", "--adaptive-fleet", "--continuous", "--port", str(port)],
            stdout=log, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        base = "http://127.0.0.1:" + str(port)
        for _ in range(60):
            try:
                with opener.open(base + "/api/learning/control", timeout=2) as response:
                    control = json.load(response)
                break
            except OSError:
                if child.poll() is not None: raise RuntimeError("Installed dashboard exited")
                time.sleep(1)
        else: raise RuntimeError("Installed dashboard did not become ready")
        audit = exe.parent / "_internal" / "app" / "verify_live_dashboard_ui.py"
        ui = subprocess.run([str(exe), "-u", str(audit), "--base", base],
            capture_output=True, text=True, encoding="utf-8", timeout=150)
        if ui.returncode:
            raise RuntimeError("Installed UI failed: " + ui.stdout[-1500:] + ui.stderr[-1500:])
        report["frozen_ui"] = json.loads(ui.stdout)
        if report["frozen_ui"].get("pages_passed") != 10:
            raise RuntimeError("Not all ten installed frontend pages passed")
        try:
            with opener.open(base + "/api/operator/settings", timeout=3) as response:
                csrf = json.load(response)["csrf_token"]
            request = Request(base + "/api/operator/learning/stop", data=b"{}",
                headers={"Content-Type": "application/json", "Origin": base, "X-SURYADEV-CSRF": csrf})
            with opener.open(request, timeout=5): pass
        except OSError: pass
        report["status"] = "PASS"
        (release / "INSTALLER-INTEGRATION.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        server.shutdown(); server.server_close()
        if child is not None:
            # Only this newly created empty-workspace test process tree.
            import psutil
            try:
                parent = psutil.Process(child.pid)
                descendants = parent.children(recursive=True)
                for owned in reversed(descendants):
                    try: owned.terminate()
                    except psutil.NoSuchProcess: pass
                parent.terminate()
                psutil.wait_procs(descendants + [parent], timeout=10)
            except psutil.NoSuchProcess: pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True, type=Path)
    parser.add_argument("--install-dir", required=True, type=Path)
    args = parser.parse_args()
    run(args.release, args.install_dir)
