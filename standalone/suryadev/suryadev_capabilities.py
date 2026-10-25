"""Conservative installed-source capability discovery for SURYADEV nodes.

A package being importable is a prerequisite, NOT proof browser binaries,
provider access or comprehension. No downloads, imports or model loads.
"""
from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
import os


def installed_capabilities(root, *, installed=None):
    """Advertise only source backends that are installed or approved locally.

    Website needs a Playwright module; separately verified source smoke remains
    mandatory before treating the browser executable as operational.
    YouTube caption extraction needs yt_dlp. PDFs need pypdf.
    Plaintext/EPUB books use stdlib and an existing approved local book plan.
    """
    source = Path(root).expanduser().resolve()
    probe = installed if installed is not None else lambda name: find_spec(name) is not None
    tests = {}
    for module in ("playwright", "yt_dlp", "pypdf"):
        try:
            tests[module] = probe(module) is True
        except (ImportError, ValueError, ModuleNotFoundError):
            tests[module] = False
    can_web = tests["playwright"]
    can_captions = tests["yt_dlp"]
    can_pdf = tests["pypdf"]
    has_book_plan = False
    for name in ("book-plan.json", "book-collect-plan.json"):
        plan = source / name
        if plan.is_file():
            try:
                from suryadev_book_continuity import read_book_plan
                read_book_plan(plan)
                has_book_plan = True
            except (OSError,ValueError,TypeError,ImportError):
                # Existence is not approval; a malformed or missing-source
                # plan must not advertise work it cannot execute.
                continue
    lanes = []
    if can_web:
        lanes.append("website")
    if can_captions:
        lanes.append("youtube")
    if can_pdf:
        lanes.append("pdf")
    if has_book_plan:
        lanes.append("book")
    return {"capabilities":lanes,
            "sources": {"website":{"dependency":"playwright","installed":can_web,
                                    "browser_runtime_verified":False},
                        "youtube":{"dependency":"yt_dlp","installed":can_captions,
                                   "provider_access_verified":False},
                        "pdf":{"dependency":"pypdf","installed":can_pdf},
                        "book":{"approved_local_plan":has_book_plan}},
            "status":"installed_prerequisites_only",
            "no_network_or_runtime_download":True}
