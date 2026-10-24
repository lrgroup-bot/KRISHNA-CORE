"""Verify documented scholarly *attribution*, not someone's real-world identity.

Crossref publisher-deposited DOI metadata can corroborate an author's name and
an ORCID identifier. That is stronger than trusting a video title but it does
NOT prove the speaker in any recording is the author, nor verify credentials.
Never use this API to grant source permission or authenticate KRISHNA devices.
"""
from __future__ import annotations

import json
import re
import unicodedata
from urllib.parse import quote
from urllib.request import Request, build_opener, ProxyHandler

_DOI = re.compile(r"10\.\d{4,9}/[A-Za-z0-9._;()/:+-]{2,240}\Z")
_ORCID = re.compile(r"(\d{4}-){3}[\d]{3}[\dX]\Z")
MAX_METADATA_BYTES = 1024 * 1024


def valid_orcid(value):
    """ISO 7064 Mod 11-2 checksum, including terminal X."""
    if not isinstance(value, str) or not _ORCID.fullmatch(value):
        return False
    digits = value.replace("-", "")
    running = 0
    for char in digits[:15]:
        running = (running + int(char)) * 2
    remainder = (12 - (running % 11)) % 11
    expected = "X" if remainder == 10 else str(remainder)
    return digits[-1] == expected


def _name(value):
    return " ".join(unicodedata.normalize("NFKC", str(value or ""))
                    .casefold().split())


def crossref_metadata(doi):
    """Read bounded JSON exclusively from the official Crossref REST API."""
    if not isinstance(doi, str) or not _DOI.fullmatch(doi):
        raise ValueError("Invalid DOI")
    url = "https://api.crossref.org/works/" + quote(doi, safe="")
    req = Request(url, headers={"Accept":"application/json",
                                 "User-Agent":"SURYADEV/1.0 (public DOI attribution research)",
                                 "Accept-Encoding":"identity"})
    with build_opener(ProxyHandler({})).open(req, timeout=12) as response:
        if response.geturl().split("/")[2].lower() != "api.crossref.org":
            raise RuntimeError("Crossref metadata redirected away from official host")
        if response.headers.get("Content-Encoding","identity").lower()!="identity":
            raise RuntimeError("Compressed metadata not accepted")
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_METADATA_BYTES:
            raise RuntimeError("Oversized Crossref metadata")
        raw = response.read(MAX_METADATA_BYTES+1)
        if len(raw)>MAX_METADATA_BYTES:
            raise RuntimeError("Oversized Crossref metadata")
    return json.loads(raw)


def corroborate_scholarly_author(*, doi, orcid, person_name, metadata=None):
    """Return evidence status. Metadata authorship is not personal identity proof."""
    if not isinstance(doi, str) or not _DOI.fullmatch(doi):
        raise ValueError("Invalid scholarly DOI")
    if not valid_orcid(orcid):
        raise ValueError("A valid ORCID identifier is required")
    if not isinstance(person_name, str) or len(person_name.strip()) < 3:
        raise ValueError("Named author is required")
    row = crossref_metadata(doi) if metadata is None else metadata
    if not isinstance(row, dict) or not isinstance(row.get("message"), dict):
        raise ValueError("Crossref metadata structure invalid")
    work = row["message"]
    author_id = "https://orcid.org/" + orcid
    registered = str(work.get("DOI") or "").casefold() == doi.casefold()
    matched = False
    for person in work.get("author") or []:
        if not isinstance(person,dict):
            continue
        value = str(person.get("ORCID") or "").rstrip("/")
        full = " ".join([str(person.get("given") or "").strip(),
                         str(person.get("family") or "").strip()]).strip()
        if value.casefold() == author_id.casefold() and _name(full)==_name(person_name):
            matched = True
            break
    corroborated=bool(registered and matched)
    return {
        "schema":"suryadev.source-authority.v1",
        "doi":doi,"orcid":orcid,"person_name":person_name,
        "metadata_provider":"crossref.org",
        "doi_record_matched":registered,
        "author_orcid_name_matched":matched,
        "scholarly_attribution_correlated":corroborated,
        "human_identity_authenticated":False,
        "video_speaker_identity_authenticated":False,
        "institutional_profile_review_required":True,
        "source_text_verified":False,
        "status": ("attribution_correlated_not_identity_authenticated"
                   if corroborated else "insufficient_scholarly_attribution"),
    }
