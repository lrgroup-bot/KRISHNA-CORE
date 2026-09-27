from __future__ import annotations

"""BRAHMA/Rishi curriculum planning for SURYDEV's seven device-learning Shishya.

This is an orchestration helper, not a new knowledge authority:
- BRAHMA/BRAHMAGYAN decide the subject and Rishi perspectives.
- Garuda/Garudanetra discover public learning sources.
- SURYDEV packages a six-hour media block for one bound horse.
- Learned evidence returns through SURYDEV -> BRAHMA -> existing Rishis.

The planner is free-first.  It may use local yt-dlp for public YouTube metadata
when present; it never requires a paid API and never bypasses authentication.
"""

from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json
import re
import shutil
import subprocess
import time
import uuid


class SuryadevCurriculumPlanner:
    VERSION="suryadev-curriculum-v1"
    TARGET_SECONDS=6*60*60
    FINISH_GRACE_SECONDS=5*60
    MAX_VIDEOS=10
    MAX_CANDIDATES=40

    def __init__(self,state_root,*,brahma,brahmagyan,council,garuda_scout,memory=None):
        self.root=Path(state_root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.plans_dir=self.root/"plans"
        self.plans_dir.mkdir(parents=True,exist_ok=True)
        self.brahma=brahma
        self.brahmagyan=brahmagyan
        self.council=council
        self.garuda_scout=garuda_scout
        self.memory=memory

    @staticmethod
    def _text(value,limit=4000):
        return str(value or "").strip()[:limit]

    @staticmethod
    def _youtube_url(url):
        try:
            p=urlparse(str(url or "").strip())
        except Exception:return False
        host=(p.hostname or "").lower()
        if host in {"youtu.be","youtube.com","www.youtube.com","m.youtube.com"}:
            if host=="youtu.be":return bool(p.path.strip("/"))
            return p.path=="/watch" and bool(parse_qs(p.query).get("v"))
        return False

    @staticmethod
    def _video_id(url):
        p=urlparse(str(url or "").strip())
        if (p.hostname or "").lower()=="youtu.be":
            return p.path.strip("/").split("/")[0][:32]
        return str((parse_qs(p.query).get("v") or [""])[0])[:32]

    @classmethod
    def _duration_metadata(cls,url,timeout=25):
        """Resolve public metadata without downloading media.

        yt-dlp is optional.  Unknown duration stays unknown rather than fabricating
        a schedule.  No cookies, login or credential flags are supplied.
        """
        exe=shutil.which("yt-dlp")
        if not exe or not cls._youtube_url(url):
            return {"available":False,"reason":"yt-dlp unavailable","url":url}
        cmd=[
            exe,"--dump-single-json","--skip-download","--no-playlist",
            "--no-warnings","--no-progress",str(url),
        ]
        try:
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=max(5,int(timeout)),shell=False)
        except Exception as exc:
            return {"available":False,"reason":f"{type(exc).__name__}: {exc}","url":url}
        if p.returncode!=0:
            return {"available":False,"reason":"yt-dlp metadata lookup failed","url":url}
        try:data=json.loads(p.stdout)
        except Exception:return {"available":False,"reason":"yt-dlp returned invalid JSON","url":url}
        duration=data.get("duration")
        try:duration=float(duration)
        except (TypeError,ValueError):duration=None
        tags=[str(x).strip()[:160] for x in (data.get("tags") or []) if str(x).strip()][:40]
        return {
            "available":True,
            "url":str(data.get("webpage_url") or url)[:2000],
            "video_id":str(data.get("id") or cls._video_id(url))[:64],
            "title":str(data.get("title") or "")[:600],
            "channel":str(data.get("channel") or data.get("uploader") or "")[:300],
            "description":str(data.get("description") or "")[:3500],
            "duration_seconds":duration,
            "tags":tags,
            "availability":str(data.get("availability") or "")[:80],
            "live_status":str(data.get("live_status") or "")[:80],
            "subtitles_available":bool(data.get("subtitles") or data.get("automatic_captions")),
            "metadata_provider":"local-free:yt-dlp",
        }

    @classmethod
    def _candidate_score(cls,row):
        score=float(row.get("relevance") or 0.0)
        if row.get("subtitles_available"):score+=2.0
        source=str(row.get("channel") or row.get("source") or "").lower()
        title=str(row.get("title") or "").lower()
        authoritative_tokens=("university","institute","academy","court","government","govt","ministry",
                              "school of law","medical","science","research","lecture","course","professor")
        if any(x in source+" "+title for x in authoritative_tokens):score+=1.5
        duration=float(row.get("duration_seconds") or 0.0)
        if 20*60<=duration<=90*60:score+=1.0
        elif 8*60<=duration<=2*60*60:score+=0.4
        return round(score,4)

    @classmethod
    def select_playlist(cls,candidates,target_seconds=None,max_videos=None):
        """Bounded knapsack in one-minute bins; optimize fit first, evidence score second."""
        target=int(target_seconds or cls.TARGET_SECONDS)
        cap=int(max_videos or cls.MAX_VIDEOS)
        upper=target+cls.FINISH_GRACE_SECONDS
        usable=[]
        seen=set()
        for raw in candidates or []:
            if not isinstance(raw,dict):continue
            url=str(raw.get("url") or "").strip()
            if not cls._youtube_url(url) or url in seen:continue
            seen.add(url)
            try:duration=int(float(raw.get("duration_seconds") or 0))
            except (TypeError,ValueError):duration=0
            if duration<5*60 or duration>3*60*60:continue
            row=dict(raw);row["duration_seconds"]=duration;row["score"]=cls._candidate_score(row)
            usable.append(row)
        usable=sorted(usable,key=lambda x:(-x["score"],x["duration_seconds"]))[:cls.MAX_CANDIDATES]
        target_min=round(target/60);upper_min=round(upper/60)
        # dp[(count,total_minutes)] = (score, tuple(indices))
        dp={(0,0):(0.0,tuple())}
        for i,row in enumerate(usable):
            mins=max(1,round(row["duration_seconds"]/60))
            snapshot=list(dp.items())
            for (count,total),(score,idxs) in snapshot:
                if count>=cap:continue
                ntotal=total+mins
                if ntotal>upper_min:continue
                key=(count+1,ntotal)
                candidate=(score+float(row["score"]),idxs+(i,))
                previous=dp.get(key)
                if previous is None or candidate[0]>previous[0]:
                    dp[key]=candidate
        choices=[]
        for (count,total),(score,idxs) in dp.items():
            if count==0:continue
            delta=abs(total-target_min)
            under_penalty=0 if total>=target_min else 0.25
            choices.append((delta,under_penalty,-score,-count,total,idxs))
        if not choices:
            return {
                "selected":[],"total_seconds":0,"target_seconds":target,
                "gap_seconds":target,"fit":"NO_DURATION_CANDIDATES",
            }
        choices.sort()
        _delta,_under,_negscore,_negcount,total,idxs=choices[0]
        selected=[];cursor=0
        for pos,i in enumerate(idxs,1):
            row=dict(usable[i])
            row["order"]=pos
            row["planned_start_seconds"]=cursor
            cursor+=int(row["duration_seconds"])
            row["planned_end_seconds"]=cursor
            selected.append(row)
        gap=target-cursor
        fit=(
            "WITHIN_FINISH_GRACE" if target<=cursor<=upper else
            "UNDER_TARGET" if cursor<target else "OVER_TARGET"
        )
        return {
            "selected":selected,
            "total_seconds":cursor,
            "target_seconds":target,
            "gap_seconds":gap,
            "fit":fit,
            "max_videos":cap,
            "finish_grace_seconds":cls.FINISH_GRACE_SECONDS,
            "algorithm":"bounded minute-bin knapsack; closest duration first, evidence/relevance score second",
        }

    def _conference(self,subject,reason="",preferred_rishis=None):
        """Use the existing BRAHMA/BRAHMAGYAN knowledge-gap + perspective machinery."""
        study=self.brahma.cognitive_study_plan(subject,depth=2,limit=30,queue_gaps=True)
        mission=self.brahmagyan.create_mission(
            "BRAHMAGYAN",
            f"Learning curriculum: {subject}",
            question=(
                f"Why should the next six-hour SURYDEV learning block study {subject}, "
                "which subtopics matter most, and what evidence should the learner look for?"
            ),
            rishi_id=(preferred_rishis or [None])[0],
            knowledge_track="general",
            target_level="L4",
        )
        perspectives=self.brahmagyan.perspective_plan(
            mission["mission_id"],limit=6,preferred_rishis=preferred_rishis or [],
        )
        team=[x["rishi_id"] for x in perspectives.get("perspectives") or []]
        arguments=[]
        for row in perspectives.get("perspectives") or []:
            arguments.append({
                "rishi_id":row["rishi_id"],
                "rishi_name":row["display_name"],
                "why_this_subject":row["lens"],
                "question_for_the_block":row["research_question"],
            })
        return {
            "subject":subject,
            "reason":self._text(reason,1500),
            "mission_id":mission["mission_id"],
            "lead_rishi":mission["lead_rishi"],
            "rishi_team":team,
            "rishi_arguments":arguments,
            "existing_knowledge_and_gaps":study,
            "debate_policy":self.brahmagyan.debate_policy(mission["mission_id"],"normal"),
            "decision_rule":(
                "explicit owner/Rishi subject is accepted unless unsafe/out-of-scope; autonomous subjects come from "
                "BRAHMA knowledge gaps/curiosity. Use the existing evidence debate engine when disagreement is material."
            ),
        }

    @staticmethod
    def _search_queries(subject,perspectives,max_queries=8):
        base=[
            f'site:youtube.com/watch "{subject}" full lecture',
            f'site:youtube.com/watch "{subject}" university lecture',
            f'site:youtube.com/watch "{subject}" expert interview',
            f'site:youtube.com/watch "{subject}" course',
        ]
        for row in perspectives or []:
            question=str(row.get("question_for_the_block") or "").strip()
            if question:
                base.append(f'site:youtube.com/watch "{subject}" {question[:180]}')
        out=[];seen=set()
        for q in base:
            q=" ".join(q.split())
            if q.lower() in seen:continue
            seen.add(q.lower());out.append(q)
            if len(out)>=max_queries:break
        return out

    def choose_next_subject(self):
        """Choose the next subject from existing BRAHMA/BRAHMAGYAN learning gaps.

        Priority 1 is the explicit curiosity queue.  If no queued curiosity exists,
        reuse the Rishi learning ledger's least-trained charter assignment.  No
        random/popularity-only subject is invented here.
        """
        curiosity=self.brahmagyan.curiosity_queue(limit=20)
        if curiosity:
            row=dict(curiosity[0])
            question=self._text(row.get("question"),500)
            # A question is a valid study subject; the conference will narrow it.
            return {
                "subject":question,
                "preferred_rishis":[],
                "reason":"highest-priority existing BRAHMAGYAN curiosity/knowledge gap",
                "selection_basis":"brahmagyan_curiosity",
                "source_id":row.get("id"),
                "priority":row.get("priority"),
            }
        assignment=self.brahma.rishi_learning.next_learning_assignment()
        if assignment:
            return {
                "subject":self._text(assignment.get("subject"),500),
                "preferred_rishis":[assignment.get("rishi_id")] if assignment.get("rishi_id") else [],
                "reason":(
                    "Rishi learning ledger selected the least-trained Rishi and least-researched charter subject"
                ),
                "selection_basis":"rishi_learning_balance",
                "source_id":None,
                "priority":None,
                "rishi_assignment":assignment,
            }
        raise RuntimeError("BRAHMA has no queued curiosity or Rishi learning assignment to schedule")

    def build_next_plan(self, *, horse_id, max_videos=10, candidate_limit=40, enrich_metadata=True):
        picked=self.choose_next_subject()
        plan=self.build_six_hour_plan(
            picked["subject"],horse_id=horse_id,reason=picked["reason"],
            preferred_rishis=picked.get("preferred_rishis") or [],
            max_videos=max_videos,candidate_limit=candidate_limit,
            enrich_metadata=enrich_metadata,
        )
        plan["subject_selection"]=picked
        path=self.plans_dir/f"{plan['plan_id']}.json"
        path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding="utf-8")
        return plan

    def latest_for_horse(self,horse_id):
        hid=self._text(horse_id,80).lower()
        rows=[]
        for path in self.plans_dir.glob("SURYA-CURRICULUM-*.json"):
            try:
                row=json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if str(row.get("horse_id") or "").lower()==hid:
                rows.append(row)
        if not rows:raise KeyError(hid)
        rows.sort(key=lambda x:float(x.get("created_at") or 0),reverse=True)
        return rows[0]

    def build_six_hour_plan(self,subject,*,horse_id,reason="",preferred_rishis=None,max_videos=10,
                            candidate_limit=40,enrich_metadata=True):
        subject=self._text(subject,500)
        horse_id=self._text(horse_id,80).lower()
        if not subject:raise ValueError("curriculum subject is required")
        conference=self._conference(subject,reason,preferred_rishis)
        queries=self._search_queries(subject,conference["rishi_arguments"])
        discovered=[]
        errors=[]
        for query in queries:
            try:
                report=self.garuda_scout("BRAHMAGYAN",query,max(5,min(int(candidate_limit),12)))
            except Exception as exc:
                errors.append({"query":query,"error":f"{type(exc).__name__}: {exc}"})
                continue
            for item in report.get("web") or []:
                url=str(item.get("url") or "").strip()
                if not self._youtube_url(url):continue
                discovered.append({
                    "url":url,
                    "title":str(item.get("title") or "")[:600],
                    "summary":str(item.get("summary") or "")[:1000],
                    "source":str(item.get("source") or "web")[:120],
                    "relevance":float(item.get("relevance") or 0),
                    "discovery_query":query,
                })
                if len(discovered)>=self.MAX_CANDIDATES:break
            if len(discovered)>=self.MAX_CANDIDATES:break
        # Deduplicate before network metadata enrichment.
        unique=[];seen=set()
        for row in discovered:
            key=self._video_id(row["url"]) or row["url"]
            if key in seen:continue
            seen.add(key);unique.append(row)
        enriched=[]
        for row in unique[:max(1,min(int(candidate_limit),self.MAX_CANDIDATES))]:
            meta=self._duration_metadata(row["url"]) if enrich_metadata else {"available":False}
            merged={**row}
            if meta.get("available"):
                for key,value in meta.items():
                    if key!="available" and value not in (None,"",[],{}):merged[key]=value
            merged["metadata_available"]=bool(meta.get("available"))
            if not meta.get("available"):merged["metadata_reason"]=meta.get("reason")
            enriched.append(merged)
        packed=self.select_playlist(enriched,max_videos=max_videos)
        plan={
            "schema":"krishna.suryadev.curriculum.v1",
            "plan_id":"SURYA-CURRICULUM-"+uuid.uuid4().hex[:18],
            "horse_id":horse_id,
            "subject":subject,
            "target_seconds":self.TARGET_SECONDS,
            "max_videos":max(1,min(int(max_videos),self.MAX_VIDEOS)),
            "finish_grace_seconds":self.FINISH_GRACE_SECONDS,
            "conference":conference,
            "search_queries":queries,
            "candidate_count":len(enriched),
            "playlist":packed["selected"],
            "playlist_total_seconds":packed["total_seconds"],
            "playlist_fit":packed["fit"],
            "playlist_gap_seconds":packed["gap_seconds"],
            "backup_candidates":[x for x in enriched if x.get("url") not in {y.get("url") for y in packed["selected"]}][:8],
            "discovery_errors":errors,
            "learning_instructions":[
                "understand the screen and source context; do not merely count watch time",
                "capture source URL, title, description, tags/channel and timestamps",
                "use available captions/transcript; do not fabricate text when captions are absent",
                "extract important claims, concepts, definitions, examples, contradictions and unanswered questions",
                "raw video/audio/screen recording stays local; send distilled evidence only",
                "at six hours finish the current video only when <=5 minutes remain; otherwise checkpoint it",
                "after positive server receipt clear only the transient learning cache",
                "BRAHMA routes the learned subjects to the existing Rishis for independent web research and verification",
            ],
            "created_at":time.time(),
        }
        plan["ready"]=bool(plan["playlist"]) and packed["fit"] in {"WITHIN_FINISH_GRACE","UNDER_TARGET"}
        plan["needs_more_candidates"]=packed["total_seconds"] < self.TARGET_SECONDS-30*60
        if not any(x.get("metadata_available") for x in enriched):
            plan["ready"]=False
            plan["needs_metadata"]=True
            plan["next_action"]="resolve public video durations on an external research node/device before starting the timed block"
        path=self.plans_dir/f"{plan['plan_id']}.json"
        path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding="utf-8")
        if self.memory:
            self.memory.audit(
                "suryadev_curriculum",
                "planned",
                f"{plan['plan_id']}:{horse_id}:{subject}:{len(plan['playlist'])}:{plan['playlist_total_seconds']}s",
            )
        return plan

    def get(self,plan_id):
        path=self.plans_dir/f"{self._text(plan_id,120)}.json"
        if not path.exists():raise KeyError(plan_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def status(self):
        plans=list(self.plans_dir.glob("SURYA-CURRICULUM-*.json"))
        return {
            "component":"SURYDEV Curriculum Planner",
            "version":self.VERSION,
            "plans":len(plans),
            "target_hours":6,
            "max_videos":self.MAX_VIDEOS,
            "finish_grace_minutes":5,
            "subject_authority":"BRAHMA + existing Rishi Council/BRAHMAGYAN",
            "source_discovery":"Garuda/Garudanetra public web discovery",
            "metadata":"local-free yt-dlp when available; otherwise schedule remains unverified",
            "paid_api_required":False,
        }
