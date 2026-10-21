"""Opt-in BRAHMAGYAN handoff for one completed SURYADEV book-reading step.

Uses ONLY existing KRISHNA learning-bundle authority and pinned HTTPS pair.
Delivery receipt means BRAHMA routed candidate knowledge to Rishis; it does
not prove factual correctness, comprehension, or publishing authorization.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import time

from suryadev_book_reader import BookLedger
from suryadev_krishna_mission import load_config, post_core
from suryadev_liveops import atomic_json

REPORT = "book-handoff-runtime.json"


def canonical_digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, default=str,
                   separators=(",",":")).encode("utf-8")).hexdigest()


def bundle_for_step(ledger, book_id, mode, start_ordinal):
    if not mode.startswith("ollama:"):
        raise ValueError("extractive-only book records are NOT learned knowledge")
    info = ledger.status(book_id)
    row = ledger.db.execute(
        "SELECT start_ordinal,end_ordinal,lines_sha256,observation "
        "FROM book_journal WHERE book_id=? AND mode=? AND start_ordinal=?",
        (book_id,mode,start_ordinal)).fetchone()
    if not row:
        raise ValueError("book reading step not found")
    start,end,digest,observation = row
    if end >= info["sessions"][mode]["lines_total"] and not info["sessions"][mode]["reached_end"]:
        raise ValueError("reading session checkpoint is not committed")
    lines = ledger.db.execute(
        "SELECT ordinal,section,page_number,line_in_section,text FROM book_lines "
        "WHERE book_id=? AND ordinal BETWEEN ? AND ? ORDER BY ordinal",
        (book_id,start,end)).fetchall()
    if len(lines) != end-start+1 or ledger._step_digest(lines) != digest:
        raise ValueError("book source evidence digest does not match journal")
    source_hash = info["source_sha256"]
    job_id = ("suryadev-book-" + source_hash[:24] + "-" +
              hashlib.sha256(mode.encode("utf-8")).hexdigest()[:8] +
              "-" + str(start))
    text = (
        "Candidate book reading observation, NOT independently fact-checked. "
        "Book SHA-256: "+source_hash+", source lines "+str(start)+"-"+str(end)+
        ", source-step SHA-256: "+digest+".\n"+str(observation)[:6500])
    return {
        "schema":"krishna.suryadev.learning-bundle.v1",
        "raw_media_included":False,
        "job_id":job_id,
        "project":"BRAHMAGYAN",
        "source":{"url":"local-book-sha256:"+source_hash,
                  "title":info["title"][:250],
                  "subject":"Locally approved book reading"},
        "learning_chunks":[{
            "topic":"Book: "+info["title"][:180]+", lines "+str(start)+"-"+str(end),
            "text":text[:8000],
            "modality":"book_text_interpretation_unverified",
            "confidence":0.40
        }],
        "visual_evidence":[]
    }


class BookHandoff:
    def __init__(self, root, config_file, *, transport=post_core, clock=time.time):
        self.root = Path(root).resolve()
        self.config = load_config(config_file)
        self.transport = transport
        self.clock = clock
        self.next_due = 0

    def tick(self, *, approved_book_ids, max_per_cycle=1):
        now = self.clock()
        if now < self.next_due:
            return None
        self.next_due = now + 20
        if type(max_per_cycle) is not int or not 1 <= max_per_cycle <= 5:
            raise ValueError("invalid Core handoff upload limit")
        ledger = BookLedger(self.root)
        try:
            ledger.db.execute("""
                CREATE TABLE IF NOT EXISTS book_delivery (
                   job_id TEXT PRIMARY KEY, book_id TEXT NOT NULL,
                   mode TEXT NOT NULL, start_ordinal INTEGER NOT NULL,
                   bundle_sha256 TEXT NOT NULL, receipt_id TEXT NOT NULL,
                   accepted_chunks INTEGER NOT NULL, created_at REAL NOT NULL
                )
            """)
            ledger.db.commit()
            ids = list(dict.fromkeys(approved_book_ids))
            if not ids:
                return None
            marks = ",".join("?" for _ in ids)
            sql = (
                "SELECT j.book_id,j.mode,j.start_ordinal FROM book_journal j "
                "JOIN book_sessions s ON s.book_id=j.book_id AND s.mode=j.mode "
                "LEFT JOIN book_delivery d ON d.book_id=j.book_id AND "
                "d.mode=j.mode AND d.start_ordinal=j.start_ordinal "
                "WHERE j.mode LIKE 'ollama:%' AND j.book_id IN ("+marks+") "
                "AND j.end_ordinal < s.next_ordinal AND d.job_id IS NULL "
                "ORDER BY j.recorded_at ASC LIMIT ?")
            candidates = ledger.db.execute(sql, (*ids,max_per_cycle)).fetchall()
            if not candidates:
                return None
            sent = []
            for book_id,mode,start in candidates:
                bundle = bundle_for_step(ledger,book_id,mode,start)
                digest = canonical_digest(bundle)
                job_id = bundle["job_id"]
                try:
                    reply = self.transport(self.config, "/api/suryadev/learning-bundle", {
                        "device_id":self.config["device_id"],"bundle":bundle})
                    if (reply.get("job_id") != job_id or
                            reply.get("bundle_sha256") != digest or
                            not isinstance(reply.get("accepted_chunks"),int) or
                            reply["accepted_chunks"] < 1 or
                            not reply.get("cleanup_authorized") or
                            not reply.get("receipt_id")):
                        raise ValueError("KRISHNA BRAHMAGYAN receipt mismatch or not routed")
                    with ledger.db:
                        ledger.db.execute(
                            "INSERT INTO book_delivery VALUES(?,?,?,?,?,?,?,?)",
                            (job_id,book_id,mode,start,digest,reply["receipt_id"],
                             reply["accepted_chunks"],now))
                    sent.append({"job_id":job_id,"book_id":book_id,
                        "receipt_id":reply["receipt_id"],
                        "bundle_sha256":digest,"brahmagyan_candidate_routed":True,
                        "rishi_factual_verification_complete":False})
                except (OSError,ValueError,RuntimeError,TypeError) as exc:
                    result={"status":"retry_later","error":type(exc).__name__+
                            ": "+str(exc)[:180], "job_id":job_id,
                            "brahmagyan_candidate_routed":False,
                            "next_attempt_at":now+300}
                    self.next_due = now+300
                    atomic_json(self.root,REPORT,result)
                    return result
            result={"status":"candidate_receipts_recorded","receipts":sent,
                    "brahmagyan_candidate_routed":True,
                    "rishi_factual_verification_complete":False,
                    "updated_at":now}
            atomic_json(self.root,REPORT,result)
            return result
        finally:
            ledger.close()
