"""Conservative source classification and learning-status reporting."""
from urllib.parse import urlsplit
from pathlib import PurePosixPath

def source_kind(url):
    p=urlsplit(url)
    host=(p.hostname or "").lower()
    if host in {"youtube.com","www.youtube.com","m.youtube.com","youtu.be","www.youtu.be"}:
        return "youtube"
    if PurePosixPath(p.path.lower()).suffix == ".pdf":
        return "pdf"
    if p.scheme == "file" and PurePosixPath(p.path.lower()).suffix == ".pdf":
        return "pdf"
    return "website" if p.scheme in ("http","https") else "other"

def breakdown(db):
    result={kind:{"queued":0,"running":0,"done":0,"failed":0,"total":0} for kind in ("youtube","pdf","website","other")}
    for url,status in db.execute("SELECT url,status FROM jobs"):
        group=result[source_kind(url)]
        group["total"]+=1
        if status in group:
            group[status]+=1
    return result
