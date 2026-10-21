"""BRAHMA's bounded, deterministic Rishi examination schedule.

Schedules challenging end-of-day and spaced-recall assignments without
pretending an LLM generated questions or a Rishi ran/graded an exam.
The existing BRAHMAGYAN ledger is the sole examination record authority.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
from threading import RLock
import time

SCHEMA = "krishna.brahma.rishi-exam-schedule.v1"
REVIEW_DAYS = (1, 7, 30)

class BrahmaExamScheduler:
    def __init__(self, root, brain, *, clock=time.time):
        self.root=Path(root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"rishi-exam-schedule.json"
        self.brain=brain
        self.clock=clock
        self.lock=RLock()

    def _load(self):
        if not self.path.exists():
            return {"schema":SCHEMA,"assignments":{}}
        obj=json.loads(self.path.read_text(encoding="utf-8"))
        if (not isinstance(obj,dict) or obj.get("schema")!=SCHEMA
                or not isinstance(obj.get("assignments"),dict)):
            raise RuntimeError("BRAHMA exam schedule damaged; refusing overwrite")
        return obj

    def _save(self,state):
        tmp=self.path.with_suffix(".tmp")
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(state,f,ensure_ascii=False,sort_keys=True,indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp,self.path)

    def plan(self, *, as_of=None, include_unready=False):
        """Schedule initial Rishi exam and recall anchored to a passed exam date."""
        day=date.fromisoformat(as_of) if as_of is not None else datetime.fromtimestamp(self.clock(),timezone.utc).date()
        missions=self.brain.missions(limit=500)
        with self.lock:
            state=self._load()
            added=[]
            candidates=self.brain.collector_candidates(limit=500).get("items",[])
            for mission in missions:
                if not isinstance(mission,dict):
                    continue
                mid=mission.get("mission_id")
                if not mid or mission.get("status") in ("cancelled","rejected"):
                    continue
                evidence=sum(1 for c in candidates if c.get("topic")==mission.get("topic"))
                claim_count=len(mission.get("claim_ids") or [])
                if not (include_unready or claim_count or evidence):
                    continue
                topic=str(mission.get("topic") or "")[:200]
                council=self.brain.council
                leader=council.get(mission.get("lead_rishi"))
                reviewer=next((r for r in council.select(topic,6)
                               if r["id"]!=leader["id"] and r["tier"] in ("rishi","acharya")),None)
                if reviewer is None:
                    reviewer=next((r for r in council.list()
                                   if r["id"]!=leader["id"] and r["tier"] in ("rishi","acharya")),None)
                if reviewer is None:
                    raise RuntimeError("No separate Rishi examiner is available")
                exam_state=self.brain.daily_exam_status(mid)
                exams=exam_state["exams"]
                past_days={e["date"] for e in exams}
                # A daily exam must not collide with a scheduled recall on
                # the same mission/date. Rishi evaluation stays outside BRAHMA.
                future=[]
                for e in exams:
                    if e["status"]=="passed_recorded":
                        base=date.fromisoformat(e["date"])
                        for delay in REVIEW_DAYS:
                            future.append((base+timedelta(days=delay),delay))
                # Initial assignment only if no exam or scheduled recall owns
                # that day. This also prevents repeated daemon ticks.
                scheduled_on_day=any(
                    x["mission_id"]==mid and x["exam_date"]==day.isoformat()
                    for x in state["assignments"].values())
                unissued_initial=any(
                    x["mission_id"]==mid and x["phase"]=="initial"
                    and x["status"]=="awaiting_independently_authored_questions"
                    for x in state["assignments"].values())
                if (day.isoformat() not in past_days and not scheduled_on_day
                        and not unissued_initial):
                    future.insert(0,(day,0))
                seen_dates=set()
                for due,offset in sorted(future,key=lambda x:x[0]):
                    label=due.isoformat()
                    if label in past_days or label in seen_dates:
                        continue
                    seen_dates.add(label)
                    if any(x["mission_id"]==mid and x["exam_date"]==label
                           for x in state["assignments"].values()):
                        continue
                    key=mid+":"+label+":"+str(offset)
                    row={"assignment_id":key,"mission_id":mid,"topic":topic,
                         "issued_by_rishi":leader["id"],
                         "review_by_rishi":reviewer["id"],
                         "exam_date":label,"phase":"initial" if offset==0 else "recall",
                         "recall_delay_days":offset,
                         "status":"awaiting_independently_authored_questions",
                         "questions_generated":False,"responses_graded":False,
                         "knowledge_verified":False,"evidence_candidates":evidence,
                         "claim_count":claim_count,"created_at":self.clock()}
                    state["assignments"][key]=row
                    added.append(dict(row))
            if added:self._save(state)
            return {"created":len(added),"new":added,
                    "total":len(state["assignments"]),
                    "policy":"Rishi exam assignment only; actual questions, tests and grading are separately required"}

    def due(self, *, as_of=None, limit=100):
        day=date.fromisoformat(as_of) if as_of is not None else datetime.fromtimestamp(self.clock(),timezone.utc).date()
        with self.lock:
            state=self._load()
            rows=[dict(x) for x in state["assignments"].values()
                  if x["exam_date"]<=day.isoformat()
                  and x["status"]=="awaiting_independently_authored_questions"]
            rows.sort(key=lambda x:(x["exam_date"],x["mission_id"]))
            return {"items":rows[:max(1,min(int(limit),500))],"pending":len(rows)}

    def register_issued_exam(self, assignment_id, exam_id):
        """Called only after BRAHMAGYAN validated a Rishi-created exam."""
        with self.lock:
            state=self._load()
            row=state["assignments"].get(assignment_id)
            if not row:raise KeyError(assignment_id)
            exams=self.brain.daily_exam_status(row["mission_id"])["exams"]
            matched=next((e for e in exams if e["exam_id"]==exam_id),None)
            if (matched is None or matched["issued_by_rishi_id"]!=row["issued_by_rishi"]
                    or matched["date"]!=row["exam_date"]):
                raise ValueError("exam does not match Rishi assignment and date")
            if row["status"]=="issued" and row.get("exam_id")==exam_id:
                return {**row,"idempotent":True}
            if row["status"]!="awaiting_independently_authored_questions":
                raise RuntimeError("assignment already bound to another exam")
            row.update(status="issued",exam_id=exam_id,questions_generated=True)
            self._save(state)
            return dict(row)

    def status(self):
        with self.lock:
            state=self._load()
            counts={}
            for x in state["assignments"].values():
                counts[x["status"]]=counts.get(x["status"],0)+1
            return {"schema":SCHEMA,"count":len(state["assignments"]),
                    "by_status":counts,"automatic_question_generation":False,
                    "automatic_grading":False,
                    "source":"BRAHMAGYAN Rishi Council mission ledger"}
