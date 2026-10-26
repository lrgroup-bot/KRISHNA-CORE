"""Atomic, opt-in approval of three publicly reviewed standalone test lessons.

The operator must explicitly run --approve to activate these exact sources.
No playback, mission dispatch, Core credential read, old-video retry or DB
change. One plan replacement prevents the one-time video selection from being
frozen after the first new approved source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
from urllib.parse import urlsplit

from suryadev_feeder import read_plan
from suryadev_trial_limits import video_job_id, VIDEO_FILE

LESSONS=(
    ("Python numeric types and operations",
     "https://www.youtube.com/watch?v=khKv-8q7YmY"),
    ("Python lists, tuples, and sets",
     "https://www.youtube.com/watch?v=W8KRzm-HUcc"),
    ("Python dictionaries and key-value pairs",
     "https://www.youtube.com/watch?v=daefaLgNkw0"),
)


def _read_json(path, maximum=131072):
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise RuntimeError("Unsafe or oversized evidence file: "+path.name)
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,ValueError) as exc:
        raise RuntimeError("Unreadable evidence: "+path.name) from exc
    if not isinstance(data,dict):
        raise RuntimeError("Invalid evidence format: "+path.name)
    return data


def prepare(root, *, approve=False):
    root=Path(root).expanduser().resolve(strict=True)
    plan_file=root/"learning-plan.json"
    if not plan_file.is_file() or plan_file.is_symlink():
        raise ValueError("Valid owner-approved source plan required")
    plan=read_plan(plan_file)
    if not (root/"suryadev.sqlite3").is_file():
        raise ValueError("Existing standalone SURYADEV workspace required")
    urls=[url for _,url in LESSONS]
    if len(urls)!=len(set(urls)):
        raise RuntimeError("Trial URLs must be distinct")
    for url in urls:
        p=urlsplit(url)
        if (p.scheme!="https" or p.hostname!="www.youtube.com"
                or p.path!="/watch" or p.query.count("v=")!=1
                or p.username or p.password or p.fragment or p.port not in (None,443)):
            raise ValueError("Invalid curated trial watch URL")
    candidates=[{"title":title,"url":url,"job_id":video_job_id(url)}
                for title,url in LESSONS]
    existing=set(plan["approved_urls"])
    selection=_read_json(root/VIDEO_FILE,8192)
    if selection is not None:
        ids=selection.get("job_ids")
        if (selection.get("schema")!="suryadev.video-trial-selection.v1"
                or selection.get("target")!=3 or not isinstance(ids,list)
                or ids):
            raise RuntimeError("Video trial selection is not an empty 3-video selection; no changes")
    attempted=_read_json(root/"video-observer-attempts.json")
    if attempted and (attempted.get("schema")!="suryadev.video-attempts.v1"
                      or not isinstance(attempted.get("job_ids"),list)):
        raise RuntimeError("Invalid historical attempt journal: no changes")
    attempted_ids=set(attempted.get("job_ids",[]) if attempted else [])
    history=_read_json(root/"video-review"/"runtime"/"worker-state.json")
    historical=(history.get("jobs",{}) if history else {})
    if not isinstance(historical,dict):
        raise RuntimeError("Invalid historical worker state")
    for item in candidates:
        jid=item["job_id"]
        if (jid in attempted_ids or jid in historical
                or (root/"video-review"/"runtime"/"jobs"/jid).exists()
                or (root/"video-review"/"approved-inbox"/(jid+".json")).exists()):
            raise RuntimeError("Candidate already has historical job/evidence; no replays: "+jid)
    new=[item for item in candidates if item["url"] not in existing]
    if len(new)!=3:
        raise RuntimeError("Trial source is already in the approved plan; preserve current selection")
    if len(plan["approved_urls"])+len(new)>300:
        raise RuntimeError("Approved URL plan is full")
    report={"schema":"suryadev.standalone-trial-source-batch.v1",
            "mode":"approved" if approve else "preview",
            "source_approval_modified":False,
            "worker_restarted":False,
            "krishna_contacted":False,
            "historical_video_jobs_modified":False,
            "new_lessons":candidates,
            "operator_approval_required":not approve}
    if not approve:
        return report
    updated=json.loads(plan_file.read_text(encoding="utf-8"))
    updated["approved_urls"]=list(updated["approved_urls"])+urls
    updated["allowed_source_hosts"]=list(dict.fromkeys(
        list(updated.get("allowed_source_hosts",[]))+["www.youtube.com"]))
    fd,temp=tempfile.mkstemp(prefix=".standalone-approval-",suffix=".json",dir=str(root))
    os.close(fd)
    temp=Path(temp)
    backup=root/("learning-plan.before-standalone-trial-"+
                 hashlib.sha256(plan_file.read_bytes()).hexdigest()[:12]+".json")
    try:
        temp.write_text(json.dumps(updated,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        read_plan(temp)
        # Preserve byte-exact preapproval plan before the atomic replacement.
        with backup.open("xb") as out:
            out.write(plan_file.read_bytes())
        os.replace(temp,plan_file)
    finally:
        temp.unlink(missing_ok=True)
    report["mode"]="approved"
    report["source_approval_modified"]=True
    report["operator_approval_required"]=False
    report["backup"]=str(backup)
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description="Preview or explicitly approve one atomic 3-lesson standalone batch")
    p.add_argument("--data",type=Path,required=True)
    p.add_argument("--approve",action="store_true",
                   help="Owner opt-in: add exactly these three lessons to existing approved plan")
    args=p.parse_args(argv)
    try:
        result=prepare(args.data,approve=args.approve)
    except (OSError,ValueError,RuntimeError,TypeError) as exc:
        print(json.dumps({"result":"BLOCKED_NO_MUTATION",
            "error":type(exc).__name__+": "+str(exc)[:240]},indent=2))
        return 2
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
