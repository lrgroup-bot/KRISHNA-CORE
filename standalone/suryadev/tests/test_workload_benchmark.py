"""13-source benchmark validation and truthful evidence accounting without network."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from suryadev import Library
from suryadev_workload_benchmark import select, source_snapshot, COUNTS


class WorkloadBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.books=[]
        for i in range(5):
            path=self.root/f"book-{i}.txt"
            path.write_text("Chapter "+str(i)+"\nDemo text\n",encoding="utf-8")
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            self.books.append({"path":str(path),"sha256":digest})
        self.urls={
            "pdf":[f"https://example.org/manual-{i}.pdf" for i in range(3)],
            "website":[f"https://example.org/tutorial-{i}" for i in range(2)],
            "youtube":[f"https://www.youtube.com/watch?v=trial{i}" for i in range(3)]}
        sources=sum((x for x in self.urls.values()),[])
        (self.root/"learning-plan.json").write_text(json.dumps({
            "approved_urls":sources,
            "approved_feeds":[],
            "allowed_source_hosts":["example.org","www.youtube.com"],
            "max_new_per_cycle":15,"max_queued":50}),encoding="utf-8")
        (self.root/"book-plan.json").write_text(json.dumps({
            "schema":"suryadev.book-plan.v1","lines_per_step":20,
            "books":self.books}),encoding="utf-8")
        self.library=Library(self.root)
    def tearDown(self):
        self.library.db.close()
        self.temp.cleanup()
    def test_select_exact_thirteen_approved(self):
        chosen=select(self.root)
        self.assertEqual({x:len(v) for x,v in chosen.items()},COUNTS)
        for kind in self.urls:
            self.assertEqual(chosen[kind],self.urls[kind])
        self.assertEqual(chosen["book"],[x["sha256"] for x in self.books])
    def test_reject_missing_approval_without_mutation(self):
        book_plan=self.root/"book-plan.json"
        original=book_plan.read_bytes()
        book_plan.write_text(json.dumps({
            "schema":"suryadev.book-plan.v1","books":self.books[:4],
            "lines_per_step":20}))
        with self.assertRaisesRegex(ValueError,"exactly 5"):
            select(self.root)
        self.assertNotEqual(book_plan.read_bytes(),original)
        self.assertEqual(self.library.stats().get("queued",0),0)
    def test_reject_changed_book_bytes(self):
        self.books[0]["path"]
        Path(self.books[0]["path"]).write_text("UNAPPROVED NEW TEXT")
        with self.assertRaisesRegex(ValueError,"changed"):
            select(self.root)
    def test_unprocessed_jobs_never_claim_comprehension_or_video(self):
        selection=select(self.root)
        report=source_snapshot(self.root,selection)
        self.assertEqual(len(report),13)
        for row in report.values():
            self.assertFalse(row["comprehension_verified"])
        self.assertTrue(all(report[u]["status"]=="not_queued" for u in self.urls["pdf"]))
        self.assertTrue(all(report[u]["video_observation_status"]=="not_observed"
                            for u in self.urls["youtube"]))
        self.assertTrue(all(report["book:"+d["sha256"]]["status"]=="not_indexed"
                            for d in self.books))
    def test_explicit_selection_rejects_unapproved_url(self):
        chosen=select(self.root)
        manifest={
            "schema":"suryadev.workload-13.v1",
            "pdf_urls":chosen["pdf"],"website_urls":chosen["website"],
            "youtube_urls":chosen["youtube"],"book_sha256":chosen["book"]}
        manifest["pdf_urls"][1]="https://unapproved.invalid/docs.pdf"
        path=self.root/"selection.json"
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,"Unapproved"):
            select(self.root,path)


if __name__=="__main__":
    unittest.main()
