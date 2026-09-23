"""Resumable chunk transfer primitives with end-to-end hash verification."""
from pathlib import Path
import hashlib
CHUNK=4*1024*1024

def digest(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(CHUNK),b""): h.update(b)
 return h.hexdigest()

def _prefix_matches(source,target,size):
 if size<=0:return True
 with Path(source).open("rb") as a,Path(target).open("rb") as b:
  remaining=size
  while remaining:
   amount=min(CHUNK,remaining)
   left=a.read(amount); right=b.read(amount)
   if left!=right:return False
   if not left:return False
   remaining-=len(left)
 return True

def resume_copy(source,target):
 s,t=Path(source),Path(target); t.parent.mkdir(parents=True,exist_ok=True)
 if not s.is_file():raise FileNotFoundError(str(s))
 offset=t.stat().st_size if t.exists() else 0
 if offset>s.stat().st_size or (offset and not _prefix_matches(s,t,offset)):
  t.unlink(missing_ok=True); offset=0
 with s.open("rb") as a,t.open("ab") as b:
  a.seek(offset)
  for chunk in iter(lambda:a.read(CHUNK),b""): b.write(chunk)
 if digest(s)!=digest(t):
  t.unlink(missing_ok=True)
  raise IOError("transfer hash mismatch")
 return {"bytes":t.stat().st_size,"sha256":digest(t)}
