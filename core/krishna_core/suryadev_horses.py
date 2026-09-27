from __future__ import annotations

"""SURYDEV's seven permanent device Shishya ("horses").

This module is intentionally a thin edge-device coordination layer. It does not
replace BRAHMA, BRAHMAGYAN, the Rishi Council, Garuda/Garudanetra, or the existing
temporary research-Shishya lifecycle.

Each horse owns one device session at a time:
- observe/read the screen and current media source;
- preserve source/title/description/tags/timestamps/transcript evidence;
- send distilled learning batches upstream;
- keep raw recordings local;
- delete transient local data only after a positive server receipt.

SURYDEV coordinates the horses. BRAHMA remains the learning router and the existing
Rishis remain subject-matter owners.
"""

from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json
import os
import time
import uuid

from .suryadev_device_profile import SuryadevDeviceSelector


HORSE_PROFILES=(
    {
        "id":"gayatri","display_name":"Gayatri","sanskrit_name":"Gāyatrī",
        "role":"SURYDEV permanent device-learning Shishya",
        "preferred_device_class":"ipad",
        "preferred_slot":"SURYA-IPAD-01",
    },
    {
        "id":"brihati","display_name":"Brihati","sanskrit_name":"Bṛhatī",
        "role":"SURYDEV permanent device-learning Shishya",
        "preferred_device_class":"macbook",
        "preferred_slot":"SURYA-MACBOOK-01",
    },
    {
        "id":"jagati","display_name":"Jagati","sanskrit_name":"Jagatī",
        "role":"SURYDEV permanent device-learning Shishya",
        "preferred_device_class":"mobile",
        "preferred_slot":"SURYA-MOBILE-01",
    },
    {
        "id":"ushnih","display_name":"Ushnih","sanskrit_name":"Uṣṇik",
        "role":"SURYDEV permanent device-learning Shishya",
        "preferred_device_class":"unassigned",
        "preferred_slot":None,
    },
    {
        "id":"trishtubh","display_name":"Trishtubh","sanskrit_name":"Triṣṭubh",
        "role":"SURYDEV permanent device-learning Shishya",
        "preferred_device_class":"unassigned",
        "preferred_slot":None,
    },
    {
        "id":"anushtubh","display_name":"Anushtubh","sanskrit_name":"Anuṣṭubh",
        "role":"SURYDEV permanent device-learning Shishya",
        "preferred_device_class":"unassigned",
        "preferred_slot":None,
    },
    {
        "id":"pankti","display_name":"Pankti","sanskrit_name":"Paṅkti",
        "role":"SURYDEV permanent device-learning Shishya",
        "preferred_device_class":"unassigned",
        "preferred_slot":None,
    },
)

HORSE_IDS=frozenset(x["id"] for x in HORSE_PROFILES)
RAW_MEDIA_KEYS=frozenset({
    "raw_media","raw_video","raw_audio","screen_recording","camera_recording",
    "frame_bytes","audio_bytes","video_bytes","screen_bytes","recording_bytes",
})


class SuryadevHorseFleet:
    VERSION="suryadev-seven-horses-v1"
    SHIFT_SECONDS=6*60*60
    FINISH_GRACE_SECONDS=5*60

    def __init__(self,state_root):
        self.root=Path(state_root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.bindings_file=self.root/"horse-bindings.json"
        self.runtime_file=self.root/"horse-runtime.json"
        self.batches_dir=self.root/"horse-batches"
        self.receipts_dir=self.root/"horse-receipts"
        self.batches_dir.mkdir(parents=True,exist_ok=True)
        self.receipts_dir.mkdir(parents=True,exist_ok=True)

    @staticmethod
    def _read_object(path):
        if not path.exists():return {}
        try:data=json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:raise RuntimeError(f"unreadable SURYDEV horse state: {path.name}: {type(exc).__name__}") from exc
        if not isinstance(data,dict):raise RuntimeError(f"invalid SURYDEV horse state: {path.name}")
        return data

    @staticmethod
    def _write_object(path,value):
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix(path.suffix+".tmp")
        tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
        os.replace(tmp,path)

    @staticmethod
    def _digest(value):
        raw=json.dumps(value,sort_keys=True,ensure_ascii=False,default=str,separators=(",",":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _text(value,limit):
        return str(value or "").strip().replace("\x00","")[:limit]

    @classmethod
    def _horse(cls,horse_id):
        hid=str(horse_id or "").strip().lower()
        row=next((dict(x) for x in HORSE_PROFILES if x["id"]==hid),None)
        if row is None:raise KeyError(hid)
        return row

    @staticmethod
    def _valid_url(value):
        value=str(value or "").strip()
        if not value:return ""
        p=urlparse(value)
        if p.scheme not in {"http","https"} or not p.netloc:
            raise ValueError("learning source URL must be http/https")
        return value[:2000]

    @classmethod
    def _reject_raw_media(cls,value,path="payload"):
        if isinstance(value,dict):
            for key,item in value.items():
                if str(key) in RAW_MEDIA_KEYS:
                    raise ValueError(f"raw media is not permitted in SURYDEV horse learning batch: {path}.{key}")
                cls._reject_raw_media(item,f"{path}.{key}")
        elif isinstance(value,list):
            for i,item in enumerate(value):
                cls._reject_raw_media(item,f"{path}[{i}]")

    def profiles(self):
        bindings=self._read_object(self.bindings_file)
        runtime=self._read_object(self.runtime_file)
        now=time.time();out=[]
        for base in HORSE_PROFILES:
            hid=base["id"]
            bind=dict(bindings.get(hid) or {})
            live=dict(runtime.get(hid) or {})
            last=float(live.get("last_seen") or 0.0)
            age=None if not last else max(0.0,now-last)
            connected=bool(bind and age is not None and age<=150.0)
            out.append({
                **dict(base),
                "permanent":True,
                "parent":"suryadev",
                "binding":bind or None,
                "workload":bind.get("workload") if bind else None,
                "max_browser_tabs":bind.get("max_browser_tabs") if bind else 0,
                "runtime":live or None,
                "connected":connected,
                "server_link":"green" if connected else "red",
                "screen_understanding":"green" if connected and live.get("screen_understanding_ok") else "red",
                "learning":"green" if connected and live.get("learning_ok") else "red",
                "age_seconds":None if age is None else round(age,1),
            })
        return out

    def auto_bind(self, *, node_id, profile, label="", approved=False):
        """Assign the best available horse from a non-secret device capability profile."""
        if not approved:
            raise PermissionError("owner/Sudarshan approval required to auto-bind a physical device")
        node_id=self._text(node_id,200)
        if not node_id:
            raise ValueError("node_id is required")
        bindings=self._read_object(self.bindings_file)
        # If this node is already bound, re-evaluate workload but preserve horse identity.
        existing=next(((hid,row) for hid,row in bindings.items() if str((row or {}).get("node_id") or "")==node_id),None)
        classified=SuryadevDeviceSelector.classify(profile)
        if existing:
            hid,row=existing
            row=dict(row or {})
            row["profile"]=classified
            row["workload"]=classified["workload"]
            row["max_browser_tabs"]=classified["max_browser_tabs"]
            row["updated_at"]=time.time()
            bindings[hid]=row
            self._write_object(self.bindings_file,bindings)
            return {"binding":row,"classification":classified,"reused_existing_horse":True}

        horse_id,classified=SuryadevDeviceSelector.choose_horse(HORSE_PROFILES,bindings,profile)
        if not horse_id:
            return {
                "binding":None,
                "classification":classified,
                "reused_existing_horse":False,
                "fleet_full":True,
                "next_action":"add another SURYDEV device-learning Shishya only if all seven permanent horse slots are already bound",
            }
        row=self.bind(
            horse_id,node_id=node_id,
            device_class=classified["device_class"],
            label=label or next((x["preferred_slot"] for x in HORSE_PROFILES if x["id"]==horse_id),None) or node_id,
            approved=True,
        )
        bindings=self._read_object(self.bindings_file)
        live=dict(bindings.get(horse_id) or row)
        live["profile"]=classified
        live["workload"]=classified["workload"]
        live["max_browser_tabs"]=classified["max_browser_tabs"]
        live["youtube_lanes"]=classified["youtube_lanes"]
        live["updated_at"]=time.time()
        bindings[horse_id]=live
        self._write_object(self.bindings_file,bindings)
        return {"binding":live,"classification":classified,"reused_existing_horse":False,"fleet_full":False}

    def bind(self,horse_id,*,node_id,device_class,label="",approved=False):
        if not approved:raise PermissionError("owner/Sudarshan approval required to bind a physical device to a SURYDEV horse")
        horse=self._horse(horse_id)
        node_id=self._text(node_id,200)
        device_class=self._text(device_class,80).lower()
        if not node_id:raise ValueError("node_id is required")
        if not device_class:raise ValueError("device_class is required")
        bindings=self._read_object(self.bindings_file)
        for hid,row in bindings.items():
            if hid!=horse["id"] and str((row or {}).get("node_id") or "")==node_id:
                raise ValueError("node_id is already bound to another SURYDEV horse")
        row={
            "horse_id":horse["id"],
            "node_id":node_id,
            "device_class":device_class,
            "label":self._text(label,240) or horse.get("preferred_slot") or node_id,
            "bound_at":time.time(),
            "owner_approved":True,
            "authority":"SURYDEV device-learning only; no Rishi/Gyan authority",
            "workload":"unclassified",
        }
        bindings[horse["id"]]=row
        self._write_object(self.bindings_file,bindings)
        return row

    def unbind(self,horse_id,*,approved=False):
        if not approved:raise PermissionError("owner/Sudarshan approval required to unbind a SURYDEV horse")
        horse=self._horse(horse_id)
        bindings=self._read_object(self.bindings_file)
        removed=bindings.pop(horse["id"],None)
        self._write_object(self.bindings_file,bindings)
        runtime=self._read_object(self.runtime_file)
        runtime.pop(horse["id"],None)
        self._write_object(self.runtime_file,runtime)
        return {"horse_id":horse["id"],"removed":bool(removed),"binding":removed}

    def _require_binding(self,horse_id,node_id):
        horse=self._horse(horse_id)
        bindings=self._read_object(self.bindings_file)
        binding=dict(bindings.get(horse["id"]) or {})
        if not binding:raise PermissionError("SURYDEV horse has no approved physical-device binding")
        if str(binding.get("node_id") or "")!=str(node_id or ""):
            raise PermissionError("SURYDEV horse Node ID does not match approved binding")
        return horse,binding

    def heartbeat(self,horse_id,*,node_id,status=None):
        horse,binding=self._require_binding(horse_id,node_id)
        status=dict(status or {})
        self._reject_raw_media(status,"heartbeat")
        runtime=self._read_object(self.runtime_file)
        row={
            "horse_id":horse["id"],
            "node_id":binding["node_id"],
            "device_class":binding["device_class"],
            "label":binding["label"],
            "last_seen":time.time(),
            "network_ok":bool(status.get("network_ok",True)),
            "screen_understanding_ok":bool(status.get("screen_understanding_ok",False)),
            "learning_ok":bool(status.get("learning_ok",False)),
            "media_playing":bool(status.get("media_playing",False)),
            "current_url":self._text(status.get("current_url"),2000),
            "current_title":self._text(status.get("current_title"),500),
            "current_shift":self._text(status.get("current_shift"),120),
            "battery_percent":status.get("battery_percent"),
            "charging":status.get("charging"),
            "thermal_state":self._text(status.get("thermal_state"),40),
            "free_storage_bytes":status.get("free_storage_bytes"),
            "pending_batches":max(0,int(status.get("pending_batches") or 0)),
            "policy":"lightweight metadata/status heartbeat; raw media never sent",
        }
        runtime[horse["id"]]=row
        self._write_object(self.runtime_file,runtime)
        return {**row,"accepted":True}

    @classmethod
    def shift_boundary(cls,elapsed_seconds,video_remaining_seconds=None):
        elapsed=max(0.0,float(elapsed_seconds or 0.0))
        remaining=None if video_remaining_seconds is None else max(0.0,float(video_remaining_seconds))
        if elapsed<cls.SHIFT_SECONDS:
            return {
                "action":"CONTINUE",
                "shift_complete":False,
                "target_seconds":cls.SHIFT_SECONDS,
                "remaining_to_target_seconds":round(cls.SHIFT_SECONDS-elapsed,1),
                "grace_seconds":cls.FINISH_GRACE_SECONDS,
            }
        if remaining is not None and 0<remaining<=cls.FINISH_GRACE_SECONDS:
            return {
                "action":"FINISH_CURRENT_VIDEO",
                "shift_complete":False,
                "grace_seconds":cls.FINISH_GRACE_SECONDS,
                "video_remaining_seconds":round(remaining,1),
                "reason":"six-hour target reached and current video has <=5 minutes remaining",
            }
        return {
            "action":"CLOSE_BATCH_AND_CHECKPOINT_VIDEO",
            "shift_complete":True,
            "grace_seconds":cls.FINISH_GRACE_SECONDS,
            "video_remaining_seconds":None if remaining is None else round(remaining,1),
        }

    def ingest_batch(self,horse_id,*,node_id,payload):
        horse,binding=self._require_binding(horse_id,node_id)
        payload=dict(payload or {})
        self._reject_raw_media(payload)
        sources=[]
        for raw in list(payload.get("sources") or [])[:80]:
            if not isinstance(raw,dict):continue
            url=self._valid_url(raw.get("url"))
            title=self._text(raw.get("title"),600)
            description=self._text(raw.get("description"),3500)
            transcript=self._text(raw.get("transcript") or raw.get("transcript_excerpt"),12000)
            screen_notes=self._text(raw.get("screen_notes"),2500)
            tags=[self._text(x,120) for x in (raw.get("tags") or []) if str(x).strip()][:40]
            source=self._text(raw.get("source") or raw.get("channel") or raw.get("publisher"),300)
            if not (url or title or transcript):continue
            try:start=max(0.0,float(raw.get("start_seconds") or 0.0))
            except (TypeError,ValueError):start=0.0
            try:end=max(start,float(raw.get("end_seconds") or start))
            except (TypeError,ValueError):end=start
            try:duration=max(0.0,float(raw.get("duration_seconds") or 0.0))
            except (TypeError,ValueError):duration=0.0
            source_row={
                "url":url,"title":title,"description":description,"tags":tags,
                "publisher":source,"transcript_excerpt":transcript,
                "transcript_sha256":hashlib.sha256(transcript.encode("utf-8")).hexdigest() if transcript else "",
                "screen_notes":screen_notes,
                "start_seconds":start,"end_seconds":end,"duration_seconds":duration,
                "source_kind":self._text(raw.get("source_kind") or "youtube",80).lower(),
            }
            source_row["source_sha256"]=self._digest(source_row)
            sources.append(source_row)
        if not sources:raise ValueError("learning batch requires at least one usable source")
        batch={
            "schema":"krishna.suryadev.horse-learning-batch.v1",
            "batch_id":"SURYA-HORSE-"+uuid.uuid4().hex[:20],
            "horse_id":horse["id"],
            "horse_name":horse["display_name"],
            "node_id":binding["node_id"],
            "device_class":binding["device_class"],
            "label":binding["label"],
            "started_at":payload.get("started_at"),
            "ended_at":payload.get("ended_at") or time.time(),
            "shift_name":self._text(payload.get("shift_name"),120),
            "sources":sources,
            "source_count":len(sources),
            "raw_media_included":False,
            "temporary_device_cache_policy":"delete only after positive server receipt",
            "learning_policy":"metadata + description + tags + transcript + source + timestamps + screen understanding",
            "created_at":time.time(),
        }
        batch["batch_sha256"]=self._digest(batch)
        self._write_object(self.batches_dir/f"{batch['batch_id']}.json",batch)
        return batch

    def receipt(self,batch_id,*,routed_count,accepted,details=None):
        batch_id=self._text(batch_id,120)
        path=self.batches_dir/f"{batch_id}.json"
        if not path.exists():raise KeyError(batch_id)
        batch=self._read_object(path)
        receipt={
            "schema":"krishna.suryadev.horse-receipt.v1",
            "receipt_id":"SURYA-RECEIPT-"+uuid.uuid4().hex[:18],
            "batch_id":batch_id,
            "batch_sha256":batch.get("batch_sha256"),
            "horse_id":batch.get("horse_id"),
            "node_id":batch.get("node_id"),
            "accepted":bool(accepted),
            "routed_count":max(0,int(routed_count or 0)),
            "details":dict(details or {}),
            "received_at":time.time(),
            "cleanup_allowed":bool(accepted),
            "cleanup_scope":"transient local batch/cache only; never delete owner media/source applications",
        }
        receipt["receipt_sha256"]=self._digest(receipt)
        self._write_object(self.receipts_dir/f"{batch_id}.json",receipt)
        if accepted:
            runtime=self._read_object(self.runtime_file)
            hid=str(batch.get("horse_id") or "")
            row=dict(runtime.get(hid) or {})
            row["last_learning_batch_id"]=batch_id
            row["last_learning_at"]=time.time()
            row["learning_ok"]=True
            row["last_receipt_id"]=receipt["receipt_id"]
            runtime[hid]=row
            self._write_object(self.runtime_file,runtime)
        return receipt

    def batch(self,batch_id):
        path=self.batches_dir/f"{self._text(batch_id,120)}.json"
        if not path.exists():raise KeyError(batch_id)
        batch=self._read_object(path)
        receipt_path=self.receipts_dir/f"{batch['batch_id']}.json"
        return {
            "batch":batch,
            "receipt":self._read_object(receipt_path) if receipt_path.exists() else None,
        }

    def status(self):
        rows=self.profiles()
        return {
            "component":"SURYDEV Seven Horses",
            "version":self.VERSION,
            "parent":"SURYDEV",
            "permanent_shishya_count":len(HORSE_PROFILES),
            "horses":rows,
            "connected":sum(1 for x in rows if x["connected"]),
            "bound":sum(1 for x in rows if x["binding"]),
            "shift_policy":{
                "target_hours":6,
                "finish_current_video_if_remaining_seconds_lte":self.FINISH_GRACE_SECONDS,
                "otherwise":"checkpoint current video and close the batch",
            },
            "learning_input":[
                "screen understanding","source URL","title","description","tags",
                "publisher/channel","timestamps","transcript/captions",
            ],
            "authority":"device learning only; BRAHMA routes topics to existing Rishis",
            "auto_assignment":{
                "selector":SuryadevDeviceSelector.VERSION,
                "inputs":"non-secret system capability profile only",
                "workloads":["media_learning","web_research","hybrid","standby"],
                "fleet_full_behavior":"do not invent more workers automatically; report capacity exhaustion for owner planning",
            },
            "raw_media_transfer":False,
            "local_cleanup":"only after positive server receipt",
        }
