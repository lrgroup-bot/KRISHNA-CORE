"""Read-only, real-device Android UI Guardian via an installed local ADB.

No APK installation, screen taps, shell string interpolation, file modification
or phone permissions are performed here. Mobile-browser emulation is separate.
The owner must choose a specific, already-authorized ADB serial and app package.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

from .sudarshan_execution_contract import AdapterResult
from .sudarshan_evidence_archive import archive

_PACKAGE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)+$")
_SERIAL = re.compile(r"^[a-zA-Z0-9_.:\-]{2,128}$")


def inventory_android(*, adb_executable, device_serial, app_package,
                      authorized=False, evidence_root=None, project_id=None,
                      runner=None):
    if not authorized:
        raise PermissionError("explicit physical-device inspection approval required")
    if not isinstance(device_serial, str) or not _SERIAL.fullmatch(device_serial):
        raise ValueError("specific local Android device serial required")
    if not isinstance(app_package, str) or not _PACKAGE.fullmatch(app_package):
        raise ValueError("valid installed Android package required")
    adb = Path(adb_executable)
    if not adb.is_absolute() or not adb.is_file():
        raise ValueError("installed ADB binary absolute path required")
    executor = runner or subprocess.run

    def call(*args):
        argv = [str(adb), "-s", device_serial, *args]
        try:
            result = executor(argv, capture_output=True, text=True,
                              timeout=20, check=False, shell=False)
        except (OSError, subprocess.TimeoutExpired):
            raise RuntimeError("local ADB unavailable")
        if result.returncode != 0:
            raise RuntimeError("ADB command returned failure")
        output = result.stdout or ""
        if len(output) > 2_000_000:
            raise RuntimeError("Android device output exceeds safe limit")
        return output

    try:
        if call("get-state").strip() != "device":
            return AdapterResult("UI_GUARDIAN", "blocked", "", "ADB device not online")
        if not call("shell", "pm", "path", app_package).strip().startswith("package:"):
            return AdapterResult("UI_GUARDIAN", "blocked", "", "target Android app is not installed")
        focus = call("shell", "dumpsys", "window")
        focus_lines = [line for line in focus.splitlines()
                       if "mCurrentFocus" in line or "mFocusedApp" in line]
        if not any(app_package in line for line in focus_lines):
            return AdapterResult("UI_GUARDIAN", "not_tested", "",
                                 "target Android app is not currently foreground")
        raw = call("exec-out", "uiautomator", "dump", "/dev/tty")
    except RuntimeError as error:
        return AdapterResult("UI_GUARDIAN", "blocked", "", str(error))

    start = raw.find("<?xml")
    stop = raw.find("</hierarchy>", max(start, 0))
    if start < 0 or stop < 0:
        return AdapterResult("UI_GUARDIAN", "failed", "", "ADB did not return a UI hierarchy")
    xml = raw[start:stop + len("</hierarchy>")]
    try:
        tree = ET.fromstring(xml)
    except ET.ParseError:
        return AdapterResult("UI_GUARDIAN", "failed", "", "invalid Android UI XML")
    if tree.tag != "hierarchy":
        return AdapterResult("UI_GUARDIAN", "failed", "", "Android UI root invalid")
    nodes = list(tree.iter("node"))
    if not nodes:
        return AdapterResult("UI_GUARDIAN", "not_tested", "", "Android UI hierarchy empty")
    actionable = [
        {"id": node.get("resource-id", "")[:128],
         "desc": node.get("content-desc", "")[:160],
         "bounds": node.get("bounds", "")[:80]}
        for node in nodes if node.get("clickable") == "true"
    ]
    evidence = json.dumps(
        {"source": "android_adb_real_device", "serial_sha256": hashlib.sha256(
            device_serial.encode()).hexdigest(), "package": app_package,
         "ui_xml": xml, "clickable_inventory": actionable, "nodes": len(nodes),
         "interactions_performed": 0, "native_ui_verified": True},
        sort_keys=True, ensure_ascii=True).encode()
    if evidence_root is not None:
        evidence_id = archive(evidence_root, project_id, "UI_GUARDIAN", evidence)
    else:
        evidence_id = "sha256:" + hashlib.sha256(evidence).hexdigest()
    return AdapterResult(
        "UI_GUARDIAN", "passed", evidence_id,
        "physical Android UI inventory: %d nodes, %d clickable controls; NO buttons exercised" %
        (len(nodes), len(actionable)))
