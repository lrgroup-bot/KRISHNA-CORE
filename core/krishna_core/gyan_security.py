from __future__ import annotations

"""Security, scoping, context and replication services for Gyan-Bhandar.

These services sit behind Gyan-Bhandar; they do not create a second memory authority.
Sensitive encrypted payloads use random per-record AES-256-GCM data keys, with those
keys wrapped by Windows DPAPI. If the required crypto/runtime is unavailable the
encrypted path fails closed.
"""

from pathlib import Path
from urllib.parse import urlparse,parse_qs,unquote
import base64
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
import uuid

from .secure_vault import _dpapi_protect,_dpapi_unprotect,SecretVaultUnavailable


class GyanACL:
    ROLES={"owner","agent","reader","writer"}
    def __init__(self,path):
        self.path=Path(path)
        self.rules={}
        self.load_error=None
        self._load()

    def _load(self):
        if not self.path.exists():return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8-sig"))
            if raw.get("schema")!=1 or not isinstance(raw.get("projects"),dict):
                raise ValueError("invalid Gyan ACL schema")
            self.rules=dict(raw["projects"]);self.load_error=None
        except Exception as exc:
            self.rules={};self.load_error=f"{type(exc).__name__}: {exc}"

    def _healthy(self):
        if self.load_error:raise RuntimeError("Gyan ACL unreadable; refusing policy changes: "+self.load_error)

    def _save(self):
        self._healthy();self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix="gyan-acl-",suffix=".json",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:
                json.dump({"schema":1,"projects":self.rules},h,ensure_ascii=False,indent=2)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def grant(self,project,principal,permissions):
        self._healthy()
        project=str(project or "").strip();principal=str(principal or "").strip()
        perms=sorted({str(x).strip() for x in permissions or [] if str(x).strip()})
        allowed={"read","write","verify","admin"}
        if not project or not principal or not perms:raise ValueError("project, principal and permissions are required")
        if any(x not in allowed for x in perms):raise ValueError("invalid Gyan ACL permission")
        self.rules.setdefault(project,{})[principal]=perms;self._save()
        return {"project":project,"principal":principal,"permissions":perms}

    def revoke(self,project,principal):
        self._healthy();rows=self.rules.get(str(project),{})
        removed=rows.pop(str(principal),None) is not None
        if not rows:self.rules.pop(str(project),None)
        self._save();return removed

    def permits(self,project,principal,permission):
        self._healthy()
        # Local owner surface is always authoritative; delegated callers need an ACL.
        if str(principal)=="owner":return True
        perms=set((self.rules.get(str(project)) or {}).get(str(principal)) or [])
        return permission in perms or "admin" in perms

    def status(self):
        self._healthy()
        return {"owner":"Gyan-Bhandar ACL","projects":len(self.rules),
                "rules":sum(len(x) for x in self.rules.values()),
                "default":"deny delegated access; local owner remains authoritative"}


class GyanEnvelopeCipher:
    VERSION=1
    def __init__(self):
        self.available=self._available()

    @staticmethod
    def _available():
        if os.name!="nt":return False
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa:F401
            return True
        except ImportError:return False

    def encrypt(self,data:bytes,aad:bytes=b"")->dict:
        if not self.available:
            raise RuntimeError("Gyan envelope encryption requires Windows DPAPI + cryptography AESGCM")
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        dek=os.urandom(32);nonce=os.urandom(12)
        cipher=AESGCM(dek).encrypt(nonce,bytes(data),bytes(aad))
        wrapped=_dpapi_protect(dek,b"KRISHNA-GYAN-KEK-V1")
        return {"schema":self.VERSION,"alg":"AES-256-GCM","key_wrap":"Windows-DPAPI",
                "nonce_b64":base64.b64encode(nonce).decode("ascii"),
                "ciphertext_b64":base64.b64encode(cipher).decode("ascii"),
                "wrapped_dek_b64":base64.b64encode(wrapped).decode("ascii")}

    def decrypt(self,envelope:dict,aad:bytes=b"")->bytes:
        if not self.available:
            raise RuntimeError("Gyan envelope encryption is unavailable")
        if int(envelope.get("schema") or 0)!=self.VERSION:raise ValueError("unsupported Gyan envelope schema")
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        wrapped=base64.b64decode(envelope["wrapped_dek_b64"],validate=True)
        dek=_dpapi_unprotect(wrapped,b"KRISHNA-GYAN-KEK-V1")
        nonce=base64.b64decode(envelope["nonce_b64"],validate=True)
        cipher=base64.b64decode(envelope["ciphertext_b64"],validate=True)
        return AESGCM(dek).decrypt(nonce,cipher,bytes(aad))

    def status(self):
        return {"owner":"Gyan-Bhandar Envelope Encryption","available":self.available,
                "cipher":"AES-256-GCM","key_wrap":"Windows DPAPI","per_record_data_key":True,
                "fail_closed":True}


class GyanEncryptedStore:
    def __init__(self,root,cipher=None):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.cipher=cipher or GyanEnvelopeCipher()

    @staticmethod
    def _id(value):
        raw=str(value or "").strip()
        if not raw:raise ValueError("encrypted Gyan record id is required")
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def put(self,record_id,payload,project="KRISHNA"):
        rid=self._id(record_id);aad=f"gyan:{project}:{rid}".encode()
        raw=json.dumps(payload,ensure_ascii=False,separators=(",",":")).encode()
        env=self.cipher.encrypt(raw,aad)
        row={"record_id_hash":rid,"project":str(project),"envelope":env,"updated_at":time.time()}
        path=self.root/(rid+".json")
        tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(row,separators=(",",":")),encoding="utf-8");tmp.replace(path)
        return {"record_id_hash":rid,"project":str(project),"encrypted":True,"bytes":len(raw)}

    def get(self,record_id,project="KRISHNA"):
        rid=self._id(record_id);path=self.root/(rid+".json")
        if not path.is_file():raise KeyError(record_id)
        row=json.loads(path.read_text(encoding="utf-8"))
        if row.get("project")!=str(project):raise PermissionError("encrypted Gyan record project mismatch")
        aad=f"gyan:{project}:{rid}".encode()
        return json.loads(self.cipher.decrypt(row["envelope"],aad).decode("utf-8"))


class GyanContextCompiler:
    def __init__(self,gyan,context_governor):
        self.gyan=gyan;self.context=context_governor

    @staticmethod
    def parse_uri(uri):
        raw=str(uri or "").strip()
        p=urlparse(raw)
        if p.scheme!="gyan":raise ValueError("Gyan URI must use gyan://")
        project=unquote((p.netloc or "").strip())
        if not project:raise ValueError("Gyan URI project is required")
        q=parse_qs(p.query)
        topic=(q.get("topic") or [""])[0]
        kind=(q.get("kind") or [None])[0]
        verified=str((q.get("verified") or ["0"])[0]).lower() in {"1","true","yes"}
        return {"project":project,"topic":topic,"memory_kind":kind,"verified_only":verified}

    def compile(self,project,topic="",limit=50,verified_only=False,memory_kind=None):
        rows=self.gyan.recall(project,topic,limit,verified_only,memory_kind,False)
        items=[]
        for row in rows:
            verified=row.get("status")=="verified"
            score=(2.0 if verified else 0.0)+float(row.get("confidence") or 0)
            text=f"[{row.get('status','candidate').upper()}][{row.get('memory_kind','semantic')}] {row.get('topic')}: {row.get('lesson')}"
            items.append({"text":text,"verified":verified,"score":score,"fingerprint":row.get("fingerprint"),
                          "provenance":row.get("provenance") or {},"source":row.get("source")})
        chosen=self.context.select(items)
        return {"project":project,"topic":topic,"items":chosen,"count":len(chosen),
                "chars":sum(len(x["text"]) for x in chosen),
                "policy":"verified knowledge ranks first; candidates remain explicitly labeled; project scope never broadens implicitly"}

    def compile_uri(self,uri,limit=50):
        req=self.parse_uri(uri)
        return self.compile(req["project"],req["topic"],limit,req["verified_only"],req["memory_kind"])


class GyanSessionLearning:
    def __init__(self,gyan):
        self.gyan=gyan
    def capture(self,project,chat_id,summary,evidence=None,provenance=None):
        summary=str(summary or "").strip()
        if not summary:raise ValueError("session summary is required")
        return self.gyan.propose(
            project,f"session:{chat_id}",summary,evidence or [],0.5,"session-learning",False,
            "episodic",{**(provenance or {}),"chat_id":str(chat_id),"captured_at":time.time()},
        )


class GyanReplicaManager:
    def __init__(self,db_path,backup_root):
        self.db_path=Path(db_path).resolve()
        self.backup_root=Path(backup_root).resolve();self.backup_root.mkdir(parents=True,exist_ok=True)

    @staticmethod
    def _digest(path):
        h=hashlib.sha256()
        with Path(path).open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
        return h.hexdigest()

    def snapshot(self,label="gyan"):
        if not self.db_path.is_file():raise FileNotFoundError(str(self.db_path))
        stamp=time.strftime("%Y%m%d-%H%M%S")
        target=(self.backup_root/f"{label}-{stamp}-{uuid.uuid4().hex[:8]}.db").resolve()
        target.relative_to(self.backup_root)
        src=sqlite3.connect(str(self.db_path));dst=sqlite3.connect(str(target))
        try:src.backup(dst)
        finally:dst.close();src.close()
        digest=self._digest(target)
        manifest=target.with_suffix(".json")
        manifest.write_text(json.dumps({"schema":1,"source":str(self.db_path),"backup":str(target),
            "sha256":digest,"bytes":target.stat().st_size,"created_at":time.time()},indent=2),encoding="utf-8")
        return {"backup":str(target),"sha256":digest,"bytes":target.stat().st_size,"verified":self._digest(target)==digest}

    def status(self):
        manifests=sorted(self.backup_root.glob("*.json"),key=lambda p:p.stat().st_mtime,reverse=True)
        return {"owner":"Gyan-Bhandar Replica Manager","backup_root":str(self.backup_root),
                "snapshots":len(manifests),"latest":str(manifests[0]) if manifests else None,
                "policy":"SQLite online backup + SHA-256 manifest; local replica never replaces primary authority"}
