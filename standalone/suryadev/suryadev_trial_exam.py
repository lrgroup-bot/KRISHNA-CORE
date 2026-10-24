"""Autonomous, CLOSED-BOOK, source-gated SURYADEV recall checks.

Question keys and deterministic answer rubrics live outside the model prompt.
These are provisional checks, NOT proof that reading caused the knowledge or
an independent BRAHMAGYAN/Rishi exam. A question is eligible only when its
specific source facts appear in actual retained, processed learning evidence.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import threading
import time
from urllib.request import Request, build_opener, ProxyHandler

from suryadev_trial import BOOK, VIDEO, AUDIT_RECORD, audit_trial
from suryadev_liveops import atomic_json

EXAM_FILE="learning-trial-exam.json"
QUESTIONS=(
    {"id":"book-python3","source":"book","q":"Which major Python version does the second edition of Think Python use?",
     "terms":("python 3",),"required_evidence":("python 3",)},
    {"id":"book-turtle","source":"book","q":"Which standard Python library replaced Swampy for the turtle graphics chapter in Think Python 2e?",
     "terms":("turtle",),"required_evidence":("turtle",)},
    {"id":"video-engines","source":"video","q":"Name the three browser engines that the Playwright Python lesson identifies as supported.",
     "terms":("chromium","firefox","webkit"),
     "required_evidence":("chromium","firefox","webkit")},
)
MAX_REPLY=5000


def grade(answer, terms):
    """Deterministic rubric, no LLM self-grading."""
    text=" ".join(str(answer or "").lower().split())
    return bool(text) and all(re.search(r"(?<![a-z0-9])"+re.escape(term)+r"(?![a-z0-9])",text)
                              for term in terms)


def eligible_questions(root, db, audit):
    candidate=[]
    book=audit.get("book") or {}
    book_id=book.get("book_id")
    processed=int(book.get("model_lines_processed") or 0)
    book_evidence=""
    if book_id and processed>0 and book.get("journal_integrity")=="passed":
        rows=db.execute(
            "SELECT ordinal,text FROM book_lines WHERE book_id=? "
            "AND ordinal<=? ORDER BY ordinal LIMIT 3000",(book_id,processed)).fetchall()
        book_evidence=" ".join(row[1] for row in rows)
    video=audit.get("video") or {}
    # This must come from recorded caption or observed candidate material.
    # No YouTube description, public page, or model training knowledge qualifies.
    video_evidence=""
    if video.get("assignment_status")=="done" and video.get("captions_proven"):
        rows=db.execute(
            "SELECT COALESCE(f.excerpt,'') || ' ' || COALESCE(f.summary,'') "
            "FROM findings f JOIN jobs j ON j.id=f.job_id WHERE j.url=? "
            "ORDER BY f.id DESC LIMIT 2",(VIDEO,)).fetchall()
        video_evidence=" ".join(row[0] for row in rows)
    if video.get("candidate_chunks",0)>0:
        video_evidence+=" "+" ".join(str(x.get("candidate_text") or "")
                                     for x in video.get("what_observed") or [])
    for item in QUESTIONS:
        raw=book_evidence if item["source"]=="book" else video_evidence
        if not raw or not all(term in raw.casefold() for term in item["required_evidence"]):
            continue
        candidate.append({**item,"evidence_sha256":hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                          "source_locator":"model-processed book line ledger" if item["source"]=="book"
                          else "collected video caption/observer evidence"})
    return candidate


def ask_local(model, question, *, timeout=120):
    """One bounded local Ollama completion; never send the book or answer rubric."""
    body={"model":model,"prompt":
          "Closed-book test. Answer from your knowledge in one short sentence. "
          "Do not ask for hints or cite a source you did not actually see.\nQuestion: "+question,
          "stream":False,"think":False,
          "options":{"num_ctx":1024,"num_predict":128,"num_thread":2}}
    req=Request("http://127.0.0.1:11434/api/generate",
                data=json.dumps(body).encode(),method="POST",
                headers={"Content-Type":"application/json"})
    with build_opener(ProxyHandler({})).open(req,timeout=timeout) as response:
        answer=json.loads(response.read(64000)).get("response")
    if not isinstance(answer,str) or not answer.strip():
        raise RuntimeError("Ollama returned empty closed-book response")
    return answer[:MAX_REPLY]


class AutomaticTrialExam:
    def __init__(self, root, *, model, model_lock, observe=ask_local):
        self.root=Path(root).resolve()
        self.model=model
        self.model_lock=model_lock
        self.observe=observe
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix="suryadev-recall")
        self.future=None
        self.last_attempt=0.0

    def _evaluate(self, item):
        try:
            with self.model_lock:
                answer=self.observe(self.model,item["q"])
            passed=grade(answer,item["terms"])
            return {"question_id":item["id"],"source":item["source"],
                    "evidence_sha256":item["evidence_sha256"],
                    "source_locator":item["source_locator"],
                    "question":item["q"],"answer":answer[:1500],
                    "rubric_passed":passed,"status":"provisional_recall_pass" if passed else "recall_failed",
                    "independent_rishi_verified":False,"recorded_at":time.time()}
        except (OSError,RuntimeError,ValueError,TypeError) as exc:
            return {"question_id":item["id"],"source":item["source"],
                    "evidence_sha256":item["evidence_sha256"],
                    "status":"exam_error", "error":type(exc).__name__+": "+str(exc)[:130],
                    "independent_rishi_verified":False,"recorded_at":time.time()}

    def _load(self):
        try:
            obj=json.loads((self.root/EXAM_FILE).read_text(encoding="utf-8"))
            if obj.get("schema")=="suryadev.trial-exam.v1" and isinstance(obj.get("attempts"),list):
                return obj
        except (OSError,ValueError,TypeError):pass
        return {"schema":"suryadev.trial-exam.v1","attempts":[],
                "knowledge_mastery_verified":False,"rishi_exam_verified":False}

    def tick(self, *, db, capacity, books_active=0, videos_active=0):
        state=self._load()
        if self.future is not None and self.future.done():
            result=self.future.result()
            self.future=None
            state["attempts"].append(result)
            state["updated_at"]=time.time()
            atomic_json(self.root,EXAM_FILE,state)
        if self.future is not None:
            return state
        # Do not compete with an already full 85%-admitted source/book/video pool.
        if not capacity.get("safe") or (
            int(capacity.get("active_total") or 0)+books_active+videos_active
            >= int(capacity.get("max_total") or 0)):
            return state
        if time.monotonic()-self.last_attempt < 15:
            return state
        audit=audit_trial(self.root,db)
        asked={row.get("question_id") for row in state["attempts"]}
        pending=[q for q in eligible_questions(self.root,db,audit) if q["id"] not in asked]
        if pending:
            self.future=self.pool.submit(self._evaluate,pending[0])
            self.last_attempt=time.monotonic()
        return state

    def close(self):
        self.pool.shutdown(wait=True)
