"""Offline, read-only YouTube caption dependency check for Windows laptop.

Does NOT contact YouTube, alter the library, download browser binaries,
or claim a JavaScript runtime will resolve YouTube HTTP 429 restrictions.
"""
from __future__ import annotations

import importlib.metadata as metadata
import json
import re
import shutil
import subprocess


def package_version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def inspect():
    deno = shutil.which("deno")
    version = None
    if deno:
        try:
            output = subprocess.run([deno,"--version"],capture_output=True,
                                    text=True,timeout=5,check=True)
            match = re.search(r"(?m)^deno\s+(\d+)\.(\d+)\.(\d+)", output.stdout)
            version = match.group(0) if match else None
        except (OSError, subprocess.SubprocessError):
            version = None
    match = re.search(r"deno\s+(\d+)\.(\d+)\.(\d+)",version or "")
    runtime_ok = bool(match and tuple(map(int,match.groups())) >= (2,3,0))
    dlp = package_version("yt-dlp")
    ejs = package_version("yt-dlp-ejs")
    return {
        "yt_dlp_version":dlp, "yt_dlp_ejs_version":ejs,
        "deno_detected":bool(deno),"deno_version":version,
        "deno_supported":runtime_ok,
        "ready_for_supported_js_challenges":bool(dlp and ejs and runtime_ok),
        "youtube_http_429_solved":False,
        "suggestions": [
            *([] if dlp and ejs else ['python -m pip install -U "yt-dlp[default]"']),
            *([] if runtime_ok else ["scoop install deno  (then open a new PowerShell window)"]),
            "A JavaScript runtime improves extractor compatibility but cannot override YouTube HTTP 429.",
            "SURYADEV requests one caption language per job; set SURYADEV_CAPTION_LANG=en/hi/or if needed.",
        ]
    }


if __name__ == "__main__":
    print(json.dumps(inspect(),ensure_ascii=False,indent=2))
