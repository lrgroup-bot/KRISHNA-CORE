import tempfile
import time
import unittest
from pathlib import Path

from krishna_core.brahma_memory_intelligence import BrahmaMemoryIntelligence


class FakeCouncil:
    def specialist_team(self, topic, limit=6):
        return {
            "topic": topic,
            "members": [
                {
                    "id": "kanada",
                    "display_name": "Maharshi Kanada",
                    "role": "Physical Science",
                    "domains": ["materials", "physics", "fault analysis"],
                },
                {
                    "id": "bharadvaja",
                    "display_name": "Bharadvaja",
                    "role": "Research Method",
                    "domains": ["testing", "fault analysis", "experimentation"],
                },
                {
                    "id": "gautama",
                    "display_name": "Gautama",
                    "role": "Evidence",
                    "domains": ["evidence", "logic"],
                },
                {
                    "id": "veda-vyasa",
                    "display_name": "Veda Vyasa",
                    "role": "Knowledge Architect",
                    "domains": ["knowledge", "compilation"],
                },
            ],
        }


class FakeLearning:
    pass


class FakeMemory:
    def __init__(self):
        self.events = []

    def audit(self, category, status, detail):
        self.events.append((category, status, detail))


class BrahmaMemoryIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.memory = FakeMemory()
        self.runtime = BrahmaMemoryIntelligence(
            Path(self.tmp.name) / "memory-intelligence",
            FakeCouncil(),
            FakeLearning(),
            self.memory,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_provenance_fingerprint_is_stable(self):
        p = {"source_ref": "obs-1", "mission_id": "m1"}
        e = [{"source_url": "https://example.com/a?utm_source=x"}]
        self.assertEqual(
            self.runtime.provenance_fingerprint(p, e),
            self.runtime.provenance_fingerprint(dict(reversed(list(p.items()))), e),
        )

    def test_source_family_deduplicates_related_sources(self):
        out = self.runtime.source_summary(
            [
                {"source_url": "https://example.com/paper?id=1"},
                {"source_url": "https://example.com/paper?id=2"},
                {"source_url": "https://independent.example.org/result"},
            ]
        )
        self.assertEqual(out["evidence_count"], 3)
        self.assertEqual(out["independent_source_families"], 2)
        self.assertEqual(out["duplicate_or_related_sources"], 1)

    def test_learning_value_rewards_gap_and_reuse_but_accounts_for_cost(self):
        low = self.runtime.learning_value(
            confidence=0.9, novelty=0.1, quality=0.5, importance=0.2,
            future_reuse=0.1, knowledge_gap=0.1,
            compute_cost=0.9, network_cost=0.9, storage_cost=0.9,
        )
        high = self.runtime.learning_value(
            confidence=0.45, novelty=0.9, quality=0.9, importance=0.9,
            future_reuse=0.9, knowledge_gap=1.0,
            compute_cost=0.2, network_cost=0.1, storage_cost=0.1,
        )
        self.assertGreater(high["score"], low["score"])

    def test_temporal_supersession_preserves_history_and_as_of_queries(self):
        old = self.runtime.temporal_record(
            topic="KRISHNA Core version",
            claim="Version is 1",
            provenance={"source_ref": "commit-old"},
            evidence=[{"source_ref": "commit-old"}],
            valid_from=100.0,
            observed_at=100.0,
        )
        new = self.runtime.temporal_record(
            topic="KRISHNA Core version",
            claim="Version is 2",
            provenance={"source_ref": "commit-new"},
            evidence=[{"source_ref": "commit-new"}],
            valid_from=200.0,
            observed_at=200.0,
            supersedes=old["claim_id"],
        )
        historical = self.runtime.temporal_query("KRISHNA Core version", as_of=150.0)
        current = self.runtime.temporal_query("KRISHNA Core version", as_of=250.0)
        all_rows = self.runtime.temporal_query(
            "KRISHNA Core version", as_of=250.0, include_superseded=True
        )
        self.assertEqual(historical["claims"][0]["claim_id"], old["claim_id"])
        self.assertEqual(current["claims"][0]["claim_id"], new["claim_id"])
        self.assertEqual(len(all_rows["claims"]), 2)

    def test_contradiction_graph_preserves_resolution_history(self):
        a = self.runtime.temporal_record(
            topic="bearing", claim="noise indicates outer-race damage",
            provenance={"source_ref": "a"}, evidence=[{"source_ref": "a"}],
        )
        b = self.runtime.temporal_record(
            topic="bearing", claim="noise is caused by loose mounting",
            provenance={"source_ref": "b"}, evidence=[{"source_ref": "b"}],
        )
        con = self.runtime.contradiction_record(
            a["claim_id"], b["claim_id"], "competing fault hypotheses"
        )
        done = self.runtime.contradiction_resolve(
            con["contradiction_id"], "vibration measurement supports outer-race damage"
        )
        self.assertEqual(done["status"], "resolved")
        self.assertIn("vibration", done["resolution"])

    def test_idle_consolidation_collapses_duplicate_learning(self):
        decisions = [
            {
                "decision_id": "d1", "should_learn": True, "lead_rishi": "kanada",
                "provenance": {"source_ref": "x"},
                "recorded_finding": {"topic": "bearing", "claim": "outer race wear pattern"},
            },
            {
                "decision_id": "d2", "should_learn": True, "lead_rishi": "kanada",
                "provenance": {"source_ref": "y"},
                "recorded_finding": {"topic": "bearing", "claim": "outer race wear pattern"},
            },
        ]
        out = self.runtime.consolidate(decisions)
        self.assertEqual(len(out["clusters"]), 1)
        self.assertEqual(out["duplicates_collapsed"], 1)

    def test_memory_evaluation_reports_retrieval_and_hygiene(self):
        self.runtime.temporal_record(
            topic="test", claim="fact",
            provenance={"source_ref": "e1"}, evidence=[{"source_ref": "e1"}],
        )
        out = self.runtime.evaluate(expected_ids=["a", "b"], retrieved_ids=["a", "x"])
        self.assertEqual(out["precision"], 0.5)
        self.assertEqual(out["recall"], 0.5)
        self.assertEqual(out["provenance_completeness"], 1.0)

    def test_rishi_graph_keeps_gautama_and_vyasa_as_review_roles(self):
        graph = self.runtime.rishi_graph("bearing material vibration diagnosis")
        relations = {(x["to"], x["relation"]) for x in graph["edges"]}
        self.assertEqual(graph["lead_rishi"], "kanada")
        self.assertIn(("gautama", "epistemic_review"), relations)
        self.assertIn(("veda-vyasa", "compile"), relations)

    def test_blinded_teach_back_requires_independent_rishi_and_can_pass(self):
        challenge = self.runtime.teach_back_create(
            topic="bearing diagnosis",
            claim="bearing outer race wear causes periodic vibration",
            evidence=[{"source_ref": "measurement-1"}],
            lead_rishi="kanada",
            reviewer_rishi="bharadvaja",
        )
        self.assertTrue(challenge["original_claim_hidden"])
        result = self.runtime.teach_back_submit(
            challenge["challenge_id"],
            reviewer_rishi="bharadvaja",
            answer="periodic vibration supports bearing outer race wear",
            evidence_refs=["measurement-1"],
        )
        self.assertTrue(result["passed"])

    def test_decay_marks_stale_without_deleting_claim(self):
        old = time.time() - 40 * 86400
        row = self.runtime.temporal_record(
            topic="software API version",
            claim="API version is v1",
            provenance={"source_ref": "docs", "volatility": "software"},
            evidence=[{"source_ref": "docs"}],
            observed_at=old,
            valid_from=old,
        )
        scan = self.runtime.decay_scan(now=time.time(), ttl_days={"software": 30})
        queried = self.runtime.temporal_query(
            "software API version", include_superseded=True
        )
        self.assertEqual(scan["review_due"], 1)
        self.assertEqual(queried["claims"][0]["claim_id"], row["claim_id"])
        self.assertEqual(queried["claims"][0]["freshness"], "review_due")


if __name__ == "__main__":
    unittest.main()
