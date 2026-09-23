import tempfile
import unittest
from pathlib import Path

from krishna_core.context_governor import ContextGovernor
from krishna_core.long_context import (
    HybridRAG,
    LongContextLab,
    RecursiveBudget,
    RecursiveContextEngine,
    WeeklyLongContextScheduler,
)


class FakeGyan:
    def __init__(self):
        self.rows = [
            {
                "topic": "vehicle bearing diagnosis",
                "lesson": "Outer-race bearing damage often produces periodic vibration.",
                "status": "verified",
                "confidence": 0.95,
                "fingerprint": "bearing",
                "memory_kind": "semantic",
                "source": "lab",
                "provenance": {"source_ref": "measurement-1"},
            },
            {
                "topic": "unrelated UI note",
                "lesson": "The dashboard uses a compact navigation menu.",
                "status": "verified",
                "confidence": 0.99,
                "fingerprint": "ui",
                "memory_kind": "semantic",
                "source": "test",
                "provenance": {},
            },
            {
                "topic": "bearing candidate",
                "lesson": "Loose mounting may also change vibration.",
                "status": "candidate",
                "confidence": 0.4,
                "fingerprint": "candidate",
                "memory_kind": "semantic",
                "source": "research",
                "provenance": {},
            },
        ]

    def recall(self, project, topic=None, limit=50, verified_only=False, memory_kind=None, include_superseded=False):
        rows = list(self.rows)
        if verified_only:
            rows = [x for x in rows if x["status"] == "verified"]
        if memory_kind:
            rows = [x for x in rows if x["memory_kind"] == memory_kind]
        return rows[:limit]


class LongContextTests(unittest.TestCase):
    def test_needle_matrix_includes_middle_and_reports_zero_gap_for_perfect_runner(self):
        lab = LongContextLab()

        def runner(prompt):
            marker = "KRISHNA verification code is "
            start = prompt.index(marker) + len(marker)
            return prompt[start:].split(".", 1)[0].strip()

        out = lab.needle_matrix(
            runner,
            context_sizes=(4000, 8000),
            positions=(0.0, 0.5, 1.0),
        )
        self.assertTrue(out["passed"])
        self.assertEqual(out["total_cases"], 6)
        self.assertEqual(out["lost_in_middle"]["middle_pass_rate"], 1.0)
        self.assertEqual(out["lost_in_middle"]["middle_gap"], 0.0)
        self.assertEqual(out["context_rot"]["degradation"], 0.0)

    def test_needle_matrix_detects_middle_failure(self):
        lab = LongContextLab()

        def runner(prompt):
            marker = "KRISHNA verification code is "
            token = prompt[prompt.index(marker) + len(marker):].split(".", 1)[0].strip()
            # The exact prompt length differs with insertion position only slightly;
            # detect the middle case from equal amounts of filler around the needle.
            context = prompt.split("CONTEXT:\n", 1)[1].split("\n\nQUESTION:", 1)[0]
            idx = context.index(marker)
            ratio = idx / max(1, len(context))
            return "WRONG" if 0.40 <= ratio <= 0.60 else token

        out = lab.needle_matrix(
            runner,
            context_sizes=(6000,),
            positions=(0.0, 0.5, 1.0),
        )
        self.assertGreater(out["lost_in_middle"]["middle_gap"], 0.0)
        self.assertLess(out["pass_rate"], 1.0)

    def test_hybrid_rag_prefers_relevant_verified_memory(self):
        rag = HybridRAG(FakeGyan(), ContextGovernor(max_items=8, max_chars=10000))
        out = rag.query("KRISHNA", "bearing outer race vibration", limit=2)
        self.assertEqual(out["items"][0]["fingerprint"], "bearing")
        self.assertGreater(out["items"][0]["retrieval"]["score"], 0.0)
        self.assertIn(out["mode"], {"hybrid_lexical_fuzzy", "hybrid_dense"})

    def test_hybrid_rag_optional_dense_embedder(self):
        vectors = {
            "bearing question": [1.0, 0.0],
        }

        def embed(text):
            if text in vectors:
                return vectors[text]
            return [1.0, 0.0] if "bearing" in text.lower() else [0.0, 1.0]

        rag = HybridRAG(FakeGyan(), ContextGovernor(), embedder=embed)
        out = rag.query("KRISHNA", "bearing question", limit=1)
        self.assertEqual(out["mode"], "hybrid_dense")
        self.assertTrue(out["items"][0]["retrieval"]["dense_used"])

    def test_hybrid_rag_can_expand_associated_concepts(self):
        rag = HybridRAG(
            FakeGyan(),
            ContextGovernor(max_items=8, max_chars=10000),
            query_expander=lambda q: q + "\\nASSOCIATED CONCEPTS: bearing vibration outer race",
        )
        out = rag.query("KRISHNA", "wheel noise", limit=2)
        self.assertTrue(out["query_expanded"])
        self.assertIn("ASSOCIATED CONCEPTS:", out["retrieval_query"])
        self.assertEqual(out["items"][0]["fingerprint"], "bearing")

    def test_recursive_context_engine_obeys_call_budget(self):
        engine = RecursiveContextEngine()
        calls = []

        def worker(prompt):
            calls.append(prompt)
            if "SUB_RESULTS:" in prompt:
                return "final synthesis"
            return "evidence answer"

        context = ("irrelevant telemetry\n" * 2000) + "bearing vibration evidence\n"
        out = engine.solve(
            "What bearing vibration evidence exists?",
            context,
            worker,
            budget=RecursiveBudget(max_depth=3, max_calls=4, chunk_chars=1500, top_k=3),
        )
        self.assertLessEqual(out["calls"], 4)
        self.assertTrue(out["bounded"])
        self.assertEqual(len(calls), out["calls"])

    def test_recursive_context_engine_blocks_duplicate_calls(self):
        engine = RecursiveContextEngine()
        calls = []

        def worker(prompt):
            calls.append(prompt)
            return "answer"

        out = engine.solve(
            "question",
            "short context",
            worker,
            budget=RecursiveBudget(max_depth=2, max_calls=2, chunk_chars=2000, top_k=2),
        )
        self.assertEqual(out["calls"], 1)
        self.assertEqual(len(calls), 1)

    def test_weekly_scheduler_persists_run_and_next_due(self):
        with tempfile.TemporaryDirectory() as td:
            calls = []
            scheduler = WeeklyLongContextScheduler(
                Path(td),
                lambda: calls.append("run") or {"passed": True},
                interval_seconds=7 * 24 * 60 * 60,
                poll_seconds=3600,
            )
            before = scheduler.status()
            self.assertFalse(scheduler.due())
            out = scheduler.run_once(force=True)
            self.assertEqual(out["status"], "completed")
            self.assertEqual(calls, ["run"])
            self.assertEqual(scheduler.status()["run_count"], 1)
            self.assertGreater(
                scheduler.status()["next_run_at"],
                scheduler.status()["last_run_at"],
            )
            scheduler2 = WeeklyLongContextScheduler(
                Path(td),
                lambda: {"passed": True},
                interval_seconds=7 * 24 * 60 * 60,
                poll_seconds=3600,
            )
            self.assertEqual(scheduler2.status()["run_count"], 1)
            self.assertEqual(
                scheduler2.status()["last_run_at"],
                scheduler.status()["last_run_at"],
            )
            self.assertIsNotNone(before["next_run_at"])


if __name__ == "__main__":
    unittest.main()
