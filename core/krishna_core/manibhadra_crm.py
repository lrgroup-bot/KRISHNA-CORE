from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import shutil
import time
import uuid

PIPELINE_STAGES=("new","qualified","contacted","proposal","negotiation","won","lost")
ACTIVE_STAGES={"new","qualified","contacted","proposal","negotiation"}
STAGE_PROBABILITY={"new":0.10,"qualified":0.25,"contacted":0.40,"proposal":0.60,"negotiation":0.80,"won":1.0,"lost":0.0}
STALE_DAYS={"new":2,"qualified":3,"contacted":3,"proposal":5,"negotiation":4}


def _now()->str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix:str)->str:
    return prefix+"-"+uuid.uuid4().hex[:12]


class ManibhadraCRM:
    """Local-first CRM state for MANIBHADRA.

    The CRM stores business records locally. Cloud AI receives only explicitly
    prepared/sanitized summaries, never this file or credentials.
    """

    SCHEMA="krishna.manibhadra.crm.v1"

    def __init__(self,path:str|Path):
        self.path=Path(path).resolve()
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.backup=self.path.with_suffix(self.path.suffix+".bak")
        if not self.path.exists():
            self._write(self._empty())

    @staticmethod
    def _empty()->dict[str,Any]:
        return {
            "schema":ManibhadraCRM.SCHEMA,
            "updated_at":_now(),
            "leads":[],
            "deals":[],
            "customers":[],
            "suppliers":[],
            "products":[],
            "tasks":[],
            "activities":[],
            "connections":[],
            "settings":{
                "currency":"INR",
                "zero_spend":True,
                "cloud_reasoning":"verified_free_only",
                "owner_approval_for_external_writes":True,
            },
        }

    def _read(self)->dict[str,Any]:
        try:
            data=json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data,dict):raise ValueError("root not object")
            if data.get("schema")!=self.SCHEMA:raise ValueError("schema mismatch")
            return data
        except Exception as exc:
            if self.backup.exists():
                data=json.loads(self.backup.read_text(encoding="utf-8"))
                if isinstance(data,dict) and data.get("schema")==self.SCHEMA:
                    self._write(data,make_backup=False)
                    return data
            raise RuntimeError(f"MANIBHADRA CRM state unreadable: {type(exc).__name__}: {exc}") from exc

    def _write(self,data:dict[str,Any],*,make_backup:bool=True)->dict[str,Any]:
        data=dict(data)
        data["schema"]=self.SCHEMA
        data["updated_at"]=_now()
        tmp=self.path.with_suffix(self.path.suffix+".tmp")
        if make_backup and self.path.exists():
            try:shutil.copy2(self.path,self.backup)
            except OSError:pass
        tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
        tmp.replace(self.path)
        return data

    @staticmethod
    def _money(value:Any)->float:
        try:return round(float(value or 0),2)
        except (TypeError,ValueError):return 0.0

    @staticmethod
    def _clean_tags(values)->list[str]:
        return list(dict.fromkeys(str(x).strip() for x in (values or []) if str(x).strip()))[:30]

    def _activity(self,data:dict,kind:str,title:str,detail:str="",record_id:str|None=None)->None:
        data["activities"].insert(0,{
            "id":_id("act"),"time":_now(),"kind":kind,"title":str(title)[:240],
            "detail":str(detail)[:1000],"record_id":record_id,
        })
        del data["activities"][300:]

    def upsert_lead(self,row:dict[str,Any])->dict[str,Any]:
        data=self._read()
        rid=str(row.get("id") or "").strip()
        current=next((x for x in data["leads"] if x.get("id")==rid),None) if rid else None
        if current is None:
            current={"id":_id("lead"),"created_at":_now(),"stage":"new","score":0.0}
            data["leads"].append(current)
        stage=str(row.get("stage",current.get("stage","new"))).strip().lower()
        if stage not in PIPELINE_STAGES:raise ValueError("invalid lead stage")
        current.update({
            "name":str(row.get("name",current.get("name",""))).strip(),
            "company":str(row.get("company",current.get("company",""))).strip(),
            "email":str(row.get("email",current.get("email",""))).strip(),
            "phone":str(row.get("phone",current.get("phone",""))).strip(),
            "website":str(row.get("website",current.get("website",""))).strip(),
            "address":str(row.get("address",current.get("address",""))).strip(),
            "map_url":str(row.get("map_url",current.get("map_url",""))).strip(),
            "category":str(row.get("category",current.get("category",""))).strip(),
            "business_id":str(row.get("business_id",current.get("business_id",""))).strip(),
            "latitude":row.get("latitude",current.get("latitude")),
            "longitude":row.get("longitude",current.get("longitude")),
            "source":str(row.get("source",current.get("source","manual"))).strip(),
            "intent":str(row.get("intent",current.get("intent",""))).strip(),
            "stage":stage,
            "score":max(0.0,min(100.0,float(row.get("score",current.get("score",0)) or 0))),
            "next_action":str(row.get("next_action",current.get("next_action",""))).strip(),
            "next_action_at":str(row.get("next_action_at",current.get("next_action_at",""))).strip(),
            "tags":self._clean_tags(row.get("tags",current.get("tags",[]))),
            "updated_at":_now(),
        })
        if not current["name"] and not current["company"]:raise ValueError("lead name or company is required")
        self._activity(data,"lead","Lead saved",current.get("name") or current.get("company"),current["id"])
        self._write(data)
        return dict(current)

    def upsert_deal(self,row:dict[str,Any])->dict[str,Any]:
        data=self._read()
        rid=str(row.get("id") or "").strip()
        current=next((x for x in data["deals"] if x.get("id")==rid),None) if rid else None
        if current is None:
            current={"id":_id("deal"),"created_at":_now(),"stage":"new","last_touched_at":_now()}
            data["deals"].append(current)
        old_stage=current.get("stage")
        stage=str(row.get("stage",current.get("stage","new"))).strip().lower()
        if stage not in PIPELINE_STAGES:raise ValueError("invalid deal stage")
        current.update({
            "title":str(row.get("title",current.get("title",""))).strip(),
            "lead_id":str(row.get("lead_id",current.get("lead_id",""))).strip(),
            "customer":str(row.get("customer",current.get("customer",""))).strip(),
            "product":str(row.get("product",current.get("product",""))).strip(),
            "channel":str(row.get("channel",current.get("channel",""))).strip(),
            "value":self._money(row.get("value",current.get("value",0))),
            "expected_commission":self._money(row.get("expected_commission",current.get("expected_commission",0))),
            "probability":max(0.0,min(1.0,float(row.get("probability",STAGE_PROBABILITY.get(stage,0))))),
            "stage":stage,
            "next_action":str(row.get("next_action",current.get("next_action",""))).strip(),
            "next_action_at":str(row.get("next_action_at",current.get("next_action_at",""))).strip(),
            "notes":str(row.get("notes",current.get("notes",""))).strip(),
            "updated_at":_now(),
        })
        if not current["title"]:raise ValueError("deal title is required")
        if old_stage!=stage:current["last_touched_at"]=_now()
        self._activity(data,"deal","Deal saved",f"{current['title']} · {stage}",current["id"])
        self._write(data)
        return dict(current)

    def move_deal(self,deal_id:str,stage:str)->dict[str,Any]:
        data=self._read()
        stage=str(stage).strip().lower()
        if stage not in PIPELINE_STAGES:raise ValueError("invalid deal stage")
        deal=next((x for x in data["deals"] if x.get("id")==str(deal_id)),None)
        if not deal:raise KeyError(deal_id)
        deal["stage"]=stage;deal["probability"]=STAGE_PROBABILITY[stage]
        deal["last_touched_at"]=deal["updated_at"]=_now()
        self._activity(data,"deal","Deal moved",f"{deal.get('title')} → {stage}",deal["id"])
        self._write(data);return dict(deal)

    def add_task(self,row:dict[str,Any])->dict[str,Any]:
        data=self._read()
        title=str(row.get("title") or "").strip()
        if not title:raise ValueError("task title is required")
        task={
            "id":_id("task"),"title":title,"record_id":str(row.get("record_id") or "").strip(),
            "record_type":str(row.get("record_type") or "deal").strip(),
            "due_at":str(row.get("due_at") or "").strip(),"priority":str(row.get("priority") or "normal").lower(),
            "status":"open","created_at":_now(),"updated_at":_now(),
        }
        data["tasks"].append(task);self._activity(data,"task","Task created",title,task["id"])
        self._write(data);return dict(task)

    def complete_task(self,task_id:str)->dict[str,Any]:
        data=self._read();task=next((x for x in data["tasks"] if x.get("id")==str(task_id)),None)
        if not task:raise KeyError(task_id)
        task["status"]="done";task["updated_at"]=_now();task["completed_at"]=_now()
        self._activity(data,"task","Task completed",task.get("title",""),task["id"])
        self._write(data);return dict(task)

    def upsert_entity(self,kind:str,row:dict[str,Any])->dict[str,Any]:
        mapping={"customer":"customers","supplier":"suppliers","product":"products"}
        if kind not in mapping:raise ValueError("unsupported CRM entity")
        data=self._read();bucket=data[mapping[kind]]
        rid=str(row.get("id") or "").strip()
        current=next((x for x in bucket if x.get("id")==rid),None) if rid else None
        if current is None:
            current={"id":_id(kind),"created_at":_now()};bucket.append(current)
        if kind=="product":
            current.update({
                "name":str(row.get("name",current.get("name",""))).strip(),
                "sku":str(row.get("sku",current.get("sku",""))).strip(),
                "source":str(row.get("source",current.get("source","supplier"))).strip(),
                "supplier_id":str(row.get("supplier_id",current.get("supplier_id",""))).strip(),
                "sale_price":self._money(row.get("sale_price",current.get("sale_price",0))),
                "commission_rate":float(row.get("commission_rate",current.get("commission_rate",0)) or 0),
                "status":str(row.get("status",current.get("status","research"))).strip(),
                "url":str(row.get("url",current.get("url",""))).strip(),
                "tags":self._clean_tags(row.get("tags",current.get("tags",[]))),
                "updated_at":_now(),
            })
            if not current["name"]:raise ValueError("product name is required")
        else:
            current.update({
                "name":str(row.get("name",current.get("name",""))).strip(),
                "company":str(row.get("company",current.get("company",""))).strip(),
                "email":str(row.get("email",current.get("email",""))).strip(),
                "phone":str(row.get("phone",current.get("phone",""))).strip(),
                "location":str(row.get("location",current.get("location",""))).strip(),
                "notes":str(row.get("notes",current.get("notes",""))).strip(),
                "tags":self._clean_tags(row.get("tags",current.get("tags",[]))),
                "updated_at":_now(),
            })
            if not current["name"] and not current["company"]:raise ValueError(kind+" name or company is required")
        self._activity(data,kind,f"{kind.title()} saved",current.get("name") or current.get("company",""),current["id"])
        self._write(data);return dict(current)

    def set_connections(self,rows:list[dict[str,Any]])->dict[str,Any]:
        data=self._read();clean=[]
        for row in rows or []:
            clean.append({
                "id":str(row.get("id") or row.get("name") or _id("conn")).strip(),
                "name":str(row.get("name") or row.get("id") or "Connection").strip(),
                "state":str(row.get("state") or "WAITING_FOR_CONNECTION").strip().upper(),
                "free":bool(row.get("free",False)),
                "mode":str(row.get("mode") or "").strip(),
                "last_checked":_now(),
            })
        data["connections"]=clean;self._write(data);return {"connections":clean}

    @staticmethod
    def _parse_iso(value:str)->datetime|None:
        raw=str(value or "").strip()
        if not raw:return None
        try:
            dt=datetime.fromisoformat(raw.replace("Z","+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:return None

    def dashboard(self)->dict[str,Any]:
        data=self._read();now=datetime.now(timezone.utc)
        active=[x for x in data["deals"] if x.get("stage") in ACTIVE_STAGES]
        won=[x for x in data["deals"] if x.get("stage")=="won"]
        lost=[x for x in data["deals"] if x.get("stage")=="lost"]
        pipeline=sum(self._money(x.get("value")) for x in active)
        weighted=sum(self._money(x.get("value"))*float(x.get("probability") or 0) for x in active)
        expected_commission=sum(self._money(x.get("expected_commission"))*float(x.get("probability") or 0) for x in active)
        won_value=sum(self._money(x.get("value")) for x in won)
        won_commission=sum(self._money(x.get("expected_commission")) for x in won)
        attention=[]
        for task in data["tasks"]:
            if task.get("status")!="open":continue
            due=self._parse_iso(task.get("due_at",""))
            overdue=bool(due and due<now)
            priority=str(task.get("priority") or "normal")
            attention.append({
                "kind":"task","id":task["id"],"title":task.get("title","Task"),
                "detail":"Overdue" if overdue else (task.get("due_at") or "No due date"),
                "priority":100 if overdue else (80 if priority=="high" else 50),
                "action":"complete_task",
            })
        for deal in active:
            last=self._parse_iso(deal.get("last_touched_at") or deal.get("updated_at") or deal.get("created_at"))
            days=(now-last).total_seconds()/86400.0 if last else 999
            limit=STALE_DAYS.get(str(deal.get("stage")),4)
            if days>=limit:
                attention.append({
                    "kind":"deal","id":deal["id"],"title":deal.get("title","Deal"),
                    "detail":f"No activity for {int(days)} days · {deal.get('stage')}",
                    "priority":90+min(9,int(days-limit)),
                    "action":"follow_up",
                })
            elif not str(deal.get("next_action") or "").strip():
                attention.append({
                    "kind":"deal","id":deal["id"],"title":deal.get("title","Deal"),
                    "detail":"No next action set","priority":65,"action":"set_next_action",
                })
        for lead in data["leads"]:
            if lead.get("stage") in {"won","lost"}:continue
            if float(lead.get("score") or 0)>=70 and not str(lead.get("next_action") or "").strip():
                attention.append({
                    "kind":"lead","id":lead["id"],"title":lead.get("name") or lead.get("company","Lead"),
                    "detail":f"High intent score {float(lead.get('score') or 0):.0f} · no next action",
                    "priority":85,"action":"qualify",
                })
        attention.sort(key=lambda x:(-x["priority"],x["title"]))
        stages=[]
        for stage in PIPELINE_STAGES:
            rows=[x for x in data["deals"] if x.get("stage")==stage]
            stages.append({
                "stage":stage,"count":len(rows),
                "value":round(sum(self._money(x.get("value")) for x in rows),2),
                "deals":rows,
            })
        total_closed=len(won)+len(lost)
        conversion=(len(won)/total_closed*100.0) if total_closed else 0.0
        return {
            "schema":"krishna.manibhadra.dashboard.v1",
            "updated_at":data.get("updated_at"),
            "kpis":{
                "pipeline_value":round(pipeline,2),
                "weighted_pipeline":round(weighted,2),
                "expected_commission":round(expected_commission,2),
                "won_revenue":round(won_value,2),
                "won_commission":round(won_commission,2),
                "active_deals":len(active),
                "leads":len(data["leads"]),
                "conversion_percent":round(conversion,1),
                "open_tasks":sum(1 for x in data["tasks"] if x.get("status")=="open"),
            },
            "attention":attention[:30],
            "pipeline":stages,
            "recent_activity":data["activities"][:30],
            "connections":data["connections"],
            "counts":{k:len(data[k]) for k in ("customers","suppliers","products","leads","deals","tasks")},
            "zero_spend":True,
            "cloud_reasoning":"verified_free_only",
        }

    def records(self)->dict[str,Any]:
        data=self._read()
        return {k:data[k] for k in ("leads","deals","customers","suppliers","products","tasks","activities","connections")}

    def health(self)->dict[str,Any]:
        try:
            data=self._read()
            return {"ok":True,"component":"MANIBHADRA CRM","schema":data.get("schema"),"updated_at":data.get("updated_at"),"backup":self.backup.exists()}
        except Exception as exc:
            return {"ok":False,"component":"MANIBHADRA CRM","error":f"{type(exc).__name__}: {exc}","backup":self.backup.exists()}
