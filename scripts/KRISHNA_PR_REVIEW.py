from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/"core"))

from krishna_core.github_pr_review import GitHubPRReviewer
from krishna_core.security import DefensiveSecurityScanner

MARKER="<!-- krishna-pr-review -->"


def api(url,method="GET",body=None):
    token=os.environ.get("GITHUB_TOKEN","").strip()
    headers={"Accept":"application/vnd.github+json","User-Agent":"KRISHNA-PR-Reviewer","X-GitHub-Api-Version":"2022-11-28"}
    if token:headers["Authorization"]="Bearer "+token
    data=None if body is None else json.dumps(body).encode("utf-8")
    req=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read().decode("utf-8","replace")
        return json.loads(raw) if raw.strip() else {}


def main():
    event_path=Path(os.environ["GITHUB_EVENT_PATH"])
    event=json.loads(event_path.read_text(encoding="utf-8"))
    pr=event.get("pull_request") or {}
    number=int(pr.get("number") or event.get("number") or 0)
    repo=os.environ["GITHUB_REPOSITORY"]
    if not number:raise SystemExit("not a pull request event")
    base=f"https://api.github.com/repos/{repo}"
    files=api(f"{base}/pulls/{number}/files?per_page=100")
    diff_files=[]
    scanner=DefensiveSecurityScanner()
    security=[]
    for row in files:
        filename=str(row.get("filename") or "")
        diff_files.append({"filename":filename,"changes":int(row.get("changes") or 0),"status":row.get("status")})
        path=ROOT/filename
        if path.is_file() and path.stat().st_size<=2_000_000:
            try:security.extend(scanner.scan_text(filename,path.read_text(encoding="utf-8")))
            except (OSError,UnicodeDecodeError):pass
    checks=[]
    report=GitHubPRReviewer().review(
        {"title":pr.get("title"),"body":pr.get("body")},
        diff_files,checks,security,
    )
    lines=[
        MARKER,
        "## KRISHNA PR Review",
        "",
        f"- Changed files: **{report['changed_files']}**",
        f"- Changed lines: **{report['changed_lines']}**",
        f"- Static security findings: **{len(security)}**",
        f"- Deterministic review: **{'PASS' if report['accepted'] else 'REVIEW REQUIRED'}**",
        "",
        "### Concerns",
    ]
    lines += [f"- {x}" for x in report["concerns"]] or ["- None from the deterministic pre-review."]
    if security:
        lines += ["","### Security findings"]
        for x in security[:20]:
            lines.append(f"- {x.get('severity','?').upper()} {x.get('path')}:{x.get('line')} — {x.get('rule')}")
    lines += [
        "",
        "_This is a bounded deterministic pre-review. It never auto-merges and does not replace Project Perfection, KABACH, independent verification, or owner/Sudarshan policy._",
    ]
    body="\n".join(lines)
    out=ROOT/"krishna-pr-review.json"
    out.write_text(json.dumps(report,indent=2),encoding="utf-8")
    comments=api(f"{base}/issues/{number}/comments?per_page=100")
    existing=next((x for x in comments if MARKER in str(x.get("body") or "")),None)
    try:
        if existing:
            api(f"{base}/issues/comments/{existing['id']}","PATCH",{"body":body})
        else:
            api(f"{base}/issues/{number}/comments","POST",{"body":body})
    except urllib.error.HTTPError as exc:
        # Fork PRs or restricted tokens may be read-only; keep the review as CI evidence.
        print(f"KRISHNA review comment unavailable: HTTP {exc.code}")
    print(body)


if __name__=="__main__":
    main()
