from __future__ import annotations
import hashlib,json
from pathlib import Path

class KnowledgeIntegrityChain:
    """Append-only hash chain for verified knowledge receipts."""
    GENESIS="0"*64
    def __init__(self,path):self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
    @staticmethod
    def _digest(record):return hashlib.sha256(json.dumps(record,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    def append(self,payload):
        previous=self.GENESIS
        if self.path.is_file():
            lines=[x for x in self.path.read_text(encoding="utf-8").splitlines() if x.strip()]
            if lines:previous=json.loads(lines[-1])["record_hash"]
        body={"previous_hash":previous,"payload":payload};body["record_hash"]=self._digest(body)
        with self.path.open("a",encoding="utf-8") as h:h.write(json.dumps(body,ensure_ascii=False,sort_keys=True)+"\n")
        return body
    def verify(self):
        previous=self.GENESIS;count=0
        if not self.path.is_file():return {"valid":True,"records":0}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():continue
            row=json.loads(line);claimed=row.pop("record_hash",None)
            if row.get("previous_hash")!=previous or self._digest(row)!=claimed:return {"valid":False,"records":count}
            previous=claimed;count+=1
        return {"valid":True,"records":count,"head":previous}
