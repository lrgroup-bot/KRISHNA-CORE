"""End-to-end offline book continuity, visual checkpoints and BRAHMAGYAN receipts."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import types
import sys
import unittest
from unittest.mock import patch

from suryadev_book_reader import BookLedger, file_sha256
from suryadev_book_continuity import BookContinuity, read_book_plan, may_study_books
from suryadev_book_visuals import BookVisualAuditor
from suryadev_book_handoff import BookHandoff, canonical_digest, bundle_for_step
from suryadev_liveops import _safe_read


class BookContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / "owner-approved.txt"
        self.path.write_text("line 1\nline 2\nline 3", encoding="utf-8")
        self.plan = self.root / "book-plan.json"
        self.plan.write_text(json.dumps({
            "schema": "suryadev.book-plan.v1",
            "books": [{"path": str(self.path), "sha256": file_sha256(self.path)}],
            "lines_per_step": 1
        }), encoding="utf-8")
        self.now = [1000.0]

    def tearDown(self):
        self.tmp.cleanup()

    def clock(self):
        return self.now[0]

    def advance(self):
        self.now[0] += 11

    def test_single_idle_step_per_tick_then_finish_exact_last_line(self):
        relay = BookContinuity(self.root, self.plan, model="local-test",
                               use_ollama=True, clock=self.clock)
        self.assertIsNone(relay.tick(available=False))
        seen = []
        def fake(prompt,model):
            seen.append(prompt)
            return "Sentence understood provisionally"
        first = relay.tick(observe=fake)
        self.assertEqual(first["state"], "learning_book_step")
        self.assertEqual(first["processed_lines"], 1)
        self.assertEqual(len(seen), 1)
        self.assertIsNone(relay.tick(observe=fake))
        self.advance()
        second = relay.tick(observe=fake)
        self.assertEqual(second["processed_lines"], 2)
        self.advance()
        last = relay.tick(observe=fake)
        self.assertTrue(last["complete"])
        self.assertEqual(last["processed_lines"], 3)
        self.assertIn("line 3", seen[2])
        self.assertNotIn("line 3", seen[0])
        self.advance()
        state = relay.tick(observe=fake)
        self.assertEqual(state["state"], "approved_books_complete_or_in_cooldown")
        self.assertEqual(len(seen), 3)

    def test_change_to_book_file_fails_closed_without_journal_mutation(self):
        relay = BookContinuity(self.root, self.plan, model="test",
                               use_ollama=True, clock=self.clock)
        self.path.write_text("malicious changed book", encoding="utf-8")
        result = relay.tick(observe=lambda *a:"read")
        self.assertEqual(result["state"], "book_paused_error")
        self.assertIn("SHA-256 changed", result["error"])
        ledger = BookLedger(self.root)
        self.assertEqual(ledger.status()["books"], [])
        ledger.close()

    def test_idle_book_admission_respects_hardware_and_youtube_429(self):
        cap={"safe":True,"max_total":2,"active_total":0}
        video="https://www.youtube.com/watch?v=abcdefghijk"
        page="https://docs.python.org/3/library/asyncio.html"
        self.assertTrue(may_study_books(cap,[],youtube_rate_limited=False))
        self.assertFalse(may_study_books(cap,[video],youtube_rate_limited=False))
        self.assertTrue(may_study_books(cap,[video],youtube_rate_limited=True))
        self.assertFalse(may_study_books(cap,[page],youtube_rate_limited=True))
        self.assertFalse(may_study_books(cap,[video,page],youtube_rate_limited=True))
        self.assertFalse(may_study_books({**cap,"safe":False},[],
                                         youtube_rate_limited=True))
        self.assertFalse(may_study_books({**cap,"active_total":1},[],
                                         youtube_rate_limited=True))
        self.assertFalse(may_study_books({**cap,"max_total":0},[],
                                         youtube_rate_limited=True))

    def test_no_auto_approval_or_preview_only_learning(self):
        with self.assertRaisesRegex(ValueError,"explicitly enabled Ollama"):
            BookContinuity(self.root,self.plan,model="test",use_ollama=False)
        bad = json.loads(self.plan.read_text())
        bad["books"][0]["path"] = "relative/book.txt"
        self.plan.write_text(json.dumps(bad),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"absolute local path"):
            read_book_plan(self.plan)


class VisualBookTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.path=self.root/"picture-book.pdf"
        self.path.write_bytes(b"%PDF-dummy")
        class Reader:
            is_encrypted=False
            def __init__(self,*args,**kwargs):
                self.pages=[types.SimpleNamespace(extract_text=lambda:"page one"),
                            types.SimpleNamespace(extract_text=lambda:"page two")]
        with patch.dict(sys.modules,{"pypdf":types.SimpleNamespace(PdfReader=Reader)}):
            ledger=BookLedger(self.root)
            self.book=ledger.import_book(self.path)["book_id"]
            ledger.close()

    def tearDown(self):
        self.tmp.cleanup()

    def frames(self,path):
        yield ("PDF page 1",b"test-image-one")
        yield ("PDF page 2",b"test-image-two")

    def test_all_pages_resumed_exact_next_visual_then_mark_complete(self):
        auditor=BookVisualAuditor(self.root)
        calls=[]
        def vision(blob,label):
            calls.append(label)
            return "Model reports a chart on "+label
        kwargs={"vision":vision,"ocr":lambda blob,label:"OCR "+label,
                "pdf_frames":self.frames}
        first=auditor.run(self.book,max_items=1,**kwargs)
        self.assertEqual(first["visual_items_processed"],1)
        self.assertFalse(first["reached_known_end"])
        second=auditor.run(self.book,max_items=1,**kwargs)
        self.assertEqual(second["visual_items_processed"],2)
        self.assertTrue(second["reached_known_end"])
        third=auditor.run(self.book,max_items=1,**kwargs)
        self.assertEqual(third["new_visual_items_this_run"],0)
        self.assertEqual(calls,["PDF page 1","PDF page 2"])
        self.assertFalse(third["full_semantic_understanding_verified"])
        ledger=BookLedger(self.root)
        self.assertEqual(ledger.status(self.book)["visual_items_examined"],2)
        ledger.close()
        auditor.close()

    def test_model_error_does_not_claim_complete_or_skip_page(self):
        auditor=BookVisualAuditor(self.root)
        with self.assertRaisesRegex(RuntimeError,"model absent"):
            auditor.run(self.book,max_items=1,
                        vision=lambda *args: (_ for _ in ()).throw(RuntimeError("model absent")),
                        ocr=lambda *args:"OCR",pdf_frames=self.frames)
        self.assertFalse(auditor.ledger.db.execute(
            "SELECT 1 FROM book_visual_runs").fetchone())
        receipt=auditor.run(self.book,max_items=1,
                            vision=lambda *args:"Observed",ocr=lambda *args:"OCR",
                            pdf_frames=self.frames)
        self.assertEqual(receipt["visual_items_processed"],1)
        auditor.close()


class BookHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        file=self.root/"book.txt";file.write_text("verified source line",encoding="utf-8")
        self.ledger=BookLedger(self.root)
        self.book=self.ledger.import_book(file)["book_id"]
        self.ledger.read(self.book,model="local",observe=lambda *args:"Candidate meaning")
        token=self.root/"pair-secret.txt";token.write_text("X"*64,encoding="ascii")
        self.config=self.root/"paired-config.json"
        self.config.write_text(json.dumps({
            "schema":"suryadev.krishna-mission-connection.v1",
            "endpoint":"https://192.168.0.100:8443",
            "cert_sha256":"a"*64,
            "device_id":"suryadev-book-node",
            "token_file":str(token)
        }),encoding="utf-8")

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def test_valid_actual_sha256_core_receipt_once_and_no_raw_book_text(self):
        packets=[]
        def transport(config,path,payload):
            self.assertEqual(path,"/api/suryadev/learning-bundle")
            bundle=payload["bundle"]
            packets.append(bundle)
            self.assertFalse(bundle["raw_media_included"])
            self.assertIn("Candidate meaning",bundle["learning_chunks"][0]["text"])
            self.assertNotIn("verified source line",bundle["learning_chunks"][0]["text"])
            return {"job_id":bundle["job_id"],
                    "bundle_sha256":canonical_digest(bundle),
                    "receipt_id":"SURYA-ACK-test",
                    "accepted_chunks":1,"cleanup_authorized":True}
        relay=BookHandoff(self.root,self.config,transport=transport,clock=lambda:1000.0)
        result=relay.tick(approved_book_ids=[self.book])
        self.assertEqual(result["status"],"candidate_receipts_recorded")
        self.assertTrue(result["brahmagyan_candidate_routed"])
        self.assertFalse(result["rishi_factual_verification_complete"])
        self.assertEqual(len(packets),1)
        self.assertFalse(relay.tick(approved_book_ids=[self.book]))
        replay=BookHandoff(self.root,self.config,transport=transport,clock=lambda:1200.0)
        self.assertIsNone(replay.tick(approved_book_ids=[self.book]))
        self.assertEqual(len(packets),1)

    def test_fake_core_receipt_never_sets_ack_and_retries(self):
        relay=BookHandoff(self.root,self.config,
                          transport=lambda *args:{
                              "job_id":"wrong","bundle_sha256":"0"*64,
                              "accepted_chunks":1,"cleanup_authorized":True,
                              "receipt_id":"bogus"},clock=lambda:1000.0)
        result=relay.tick(approved_book_ids=[self.book])
        self.assertEqual(result["status"],"retry_later")
        self.assertFalse(result["brahmagyan_candidate_routed"])
        self.assertEqual(self.ledger.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='book_delivery'"
        ).fetchone(),("book_delivery",))
        self.assertEqual(self.ledger.db.execute("SELECT count(*) FROM book_delivery").fetchone()[0],0)

    def test_partially_read_book_never_routed_to_core(self):
        file=self.root/"longer.txt"
        file.write_text("first\nsecond\nthird",encoding="utf-8")
        book=self.ledger.import_book(file)["book_id"]
        self.ledger.read(book,model="local",max_steps=1,
                         observe=lambda *args:"Only first line studied")
        calls=[]
        relay=BookHandoff(self.root,self.config,
                          transport=lambda *args:calls.append(args),
                          clock=lambda:1000.0)
        self.assertIsNone(relay.tick(approved_book_ids=[book]))
        self.assertEqual(calls,[])
        self.ledger.read(book,model="local",observe=lambda *args:"Next line studied")
        good=BookHandoff(self.root,self.config,
                         transport=lambda config,path,payload:{
                             "job_id":payload["bundle"]["job_id"],
                             "bundle_sha256":canonical_digest(payload["bundle"]),
                             "receipt_id":"SURYA-ACK-test", "accepted_chunks":1,
                             "cleanup_authorized":True},clock=lambda:1100.0)
        self.assertEqual(good.tick(approved_book_ids=[book])["status"],
                         "candidate_receipts_recorded")

    def test_book_changed_after_learning_cannot_be_uploaded(self):
        file=self.root/"book.txt"
        file.write_text("changed after study",encoding="utf-8")
        calls=[]
        relay=BookHandoff(self.root,self.config,
                          transport=lambda *args:calls.append(args),
                          clock=lambda:1000.0)
        result=relay.tick(approved_book_ids=[self.book])
        self.assertEqual(result["status"],"retry_later")
        self.assertIn("source changed",result["error"])
        self.assertEqual(calls,[])

    def test_extractive_only_is_not_uploaded(self):
        self.ledger.read(self.book,use_ollama=False)
        with self.assertRaisesRegex(ValueError,"NOT learned knowledge"):
            bundle_for_step(self.ledger,self.book,"extractive_record_only",1)


if __name__=="__main__":
    unittest.main()
