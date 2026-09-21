from __future__ import annotations

import base64
import ctypes
import json
import os
import tempfile
import time
import uuid
from ctypes import wintypes
from pathlib import Path


class SecretVaultUnavailable(RuntimeError):
    pass


class _DATA_BLOB(ctypes.Structure):
    _fields_=[("cbData",wintypes.DWORD),("pbData",ctypes.POINTER(ctypes.c_byte))]


def _blob(data:bytes):
    if not data:
        return _DATA_BLOB(0,None),None
    buf=ctypes.create_string_buffer(data)
    return _DATA_BLOB(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_byte))),buf


def _dpapi_protect(data:bytes,entropy:bytes=b"KRISHNA-SECRET-VAULT-V1")->bytes:
    if os.name!="nt":
        raise SecretVaultUnavailable("Windows DPAPI is available only on Windows")
    crypt32=ctypes.windll.crypt32
    kernel32=ctypes.windll.kernel32
    in_blob,in_buf=_blob(data); ent_blob,ent_buf=_blob(entropy); out_blob=_DATA_BLOB()
    flags=0x1  # CRYPTPROTECT_UI_FORBIDDEN
    if not crypt32.CryptProtectData(ctypes.byref(in_blob),"KRISHNA",ctypes.byref(ent_blob),None,None,flags,ctypes.byref(out_blob)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData,out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _dpapi_unprotect(data:bytes,entropy:bytes=b"KRISHNA-SECRET-VAULT-V1")->bytes:
    if os.name!="nt":
        raise SecretVaultUnavailable("Windows DPAPI is available only on Windows")
    crypt32=ctypes.windll.crypt32
    kernel32=ctypes.windll.kernel32
    in_blob,in_buf=_blob(data); ent_blob,ent_buf=_blob(entropy); out_blob=_DATA_BLOB()
    desc=ctypes.c_wchar_p()
    flags=0x1
    if not crypt32.CryptUnprotectData(ctypes.byref(in_blob),ctypes.byref(desc),ctypes.byref(ent_blob),None,None,flags,ctypes.byref(out_blob)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData,out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


class SecureSecretVault:
    """Windows user-bound encrypted secret vault.

    Secret bytes are protected with DPAPI and only the encrypted blob is written to
    disk. APIs return metadata/reference IDs, never plaintext secret values.
    """

    def __init__(self,path:str|Path):
        self.path=Path(path)
        self.items={}
        self._load()

    @property
    def available(self)->bool:
        return os.name=="nt"

    def _load(self):
        if not self.path.exists():
            return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8-sig"))
            if raw.get("schema")!=1:
                return
            self.items={x["id"]:x for x in raw.get("secrets",[]) if x.get("id")}
        except Exception:
            self.items={}

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        payload={"schema":1,"backend":"windows-dpapi","secrets":list(self.items.values())}
        fd,tmp=tempfile.mkstemp(prefix="krishna-secrets-",suffix=".json",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:
                json.dump(payload,h,ensure_ascii=False,indent=2)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def put(self,name:str,provider:str,secret:str)->dict:
        if not self.available:
            raise SecretVaultUnavailable("secure persisted secrets require Windows DPAPI")
        name=str(name or "").strip();provider=str(provider or "").strip();secret=str(secret or "")
        if not name or not provider or not secret:
            raise ValueError("name, provider and secret are required")
        sid=str(uuid.uuid4())
        cipher=_dpapi_protect(secret.encode("utf-8"))
        item={"id":sid,"name":name,"provider":provider,"ciphertext_b64":base64.b64encode(cipher).decode("ascii"),"created_at":time.time()}
        self.items[sid]=item;self._save()
        return self.describe(sid)

    def delete(self,secret_id:str)->bool:
        removed=self.items.pop(str(secret_id),None) is not None
        if removed:self._save()
        return removed

    def resolve(self,secret_id:str)->str:
        item=self.items.get(str(secret_id))
        if not item:raise KeyError("secret reference not found")
        if not self.available:
            raise SecretVaultUnavailable("Windows DPAPI is unavailable")
        cipher=base64.b64decode(item["ciphertext_b64"],validate=True)
        return _dpapi_unprotect(cipher).decode("utf-8")

    def describe(self,secret_id:str)->dict:
        item=self.items.get(str(secret_id))
        if not item:raise KeyError("secret reference not found")
        return {"id":item["id"],"name":item["name"],"provider":item["provider"],"created_at":item["created_at"],"available":self.available,"backend":"windows-dpapi"}

    def list(self)->dict:
        rows=[self.describe(x) for x in self.items]
        rows.sort(key=lambda x:x["created_at"],reverse=True)
        return {"secrets":rows,"count":len(rows),"backend":"windows-dpapi","available":self.available,"policy":"plaintext is never returned by status/list APIs"}
