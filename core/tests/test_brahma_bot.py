import tempfile
import unittest
from pathlib import Path

from krishna_core.brahma_bot import BrahmaBot


class FakeCouncil:
    def specialist_team(self, topic, limit=6):
        return {
            "topic": topic,
            "members": [
                {"id": "kanada", "display_name": "Maharshi Kanada", "role": "Physical Science"},
                {"id": "bharadvaja", "display_name": "Bharadvaja", "role": "Research Method"},
                {"id": "gautama", "display_name": "Gautama", "role": "Evidence"},
                {"id": "veda-vyasa", "display_name": "Veda Vyasa", "role": "Knowledge Architect"},
            ],
        }


class FakeLearning:
    def __init__(self):
        self.findings = []
        self.questions = []
        self.existing = {}

    def record_finding(self, rishi_id, topic, claim, **kwargs):
        row = {"finding_id": f"f{len(self.findings)+1}", "rishi_id": rishi_id, "topic": topic, "claim": claim, **kwargs}
        self.findings.append(row)
        return row

    def add_open_question(self, rishi_id, topic, question, mission_id=None):
        row = {"rishi_id": rishi_id, "topic": topic, "question": question, "mission_id": mission_id}
        self.questions.append(row)
        return row

    def knowledge_packet(self, rishi_id, topic, limit=12):
        rows = list(self.existing.get(rishi_id, []))[:limit]
        return {
            "rishi_id": rishi_id,
            "display_name": rishi_id,
            "role": "test",
            "charter": {},
            "matching_findings": rows,
            "open_questions": [],
            "classical_lens": [],
        }


class FakeGyan:
    def __init__(self):
        self.proposals = []

    def propose(self, project, topic, lesson, evidence=None, confidence=0.0, source="research",
                verified=False, memory_kind="semantic", provenance=None, supersedes=None):
        row = {
            "approval_id": f"a{len(self.proposals)+1}",
            "project": project,
            "topic": topic,
            "lesson": lesson,
            "evidence": evidence or [],
            "confidence": confidence,
            "source": source,
            "verified": verified,
            "memory_kind": memory_kind,
            "provenance": provenance or {},
            "supersedes": supersedes,
            "stored": False,
            "requires_user_approval": True,
        }
        self.proposals.append(row)
        return row


class FakeMemory:
    def __init__(self):
        self.audits = []

    def audit(self, category, status, detail):
        self.audits.append((category, status, detail))


class BrahmaBotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.learning = FakeLearning()
        self.gyan = FakeGyan()
        self.memory = FakeMemory()
        self.bot = BrahmaBot(
            Path(self.tmp.name) / "brahma",
            FakeCouncil(),
            self.learning,
            self.gyan,
            self.memory,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_mobile_learning_routes_to_rishi_and_pc_deep_research(self):
        out = self.bot.plan_learning(
            source="mobile",
            topic="PCB voltage regulator fault",
            content="camera observation shows a damaged power section",
            modality="image",
            evidence=[{"observation_id": "HAW-1"}],
            confidence=0.45,
            novelty=0.8,
            quality=0.8,
        )
        self.assertTrue(out["should_learn"])
        self.assertEqual(out["lead_rishi"], "kanada")
        self.assertEqual(out["source_policy"]["deep_research_location"], "pc")
        self.assertFalse(out["source_policy"]["raw_streaming"])

    def test_intake_records_candidate_in_rishi_ledger_not_gyan(self):
        out = self.bot.intake(
            source="mobile",
            topic="motor bearing noise",
            content="new periodic noise observed",
            modality="audio",
            evidence=[{"observation_id": "HAW-AUDIO-1"}],
            provenance={"observation_id": "HAW-AUDIO-1"},
            confidence=0.4,
            novelty=0.9,
            quality=0.7,
        )
        self.assertIsNotNone(out["recorded_finding"])
        self.assertEqual(len(self.learning.findings), 1)
        self.assertEqual(self.learning.findings[0]["role"], "brahma_intake")
        self.assertEqual(len(self.gyan.proposals), 0)
        self.assertGreaterEqual(len(self.learning.questions), 1)
        self.assertIsNotNone(out["temporal_claim"])
        self.assertTrue(out["provenance"].get("brahma_provenance_fingerprint"))
        self.assertEqual(out["temporal_claim"]["rishi_id"], "kanada")

    def test_reuses_strong_rishi_knowledge_for_repetitive_low_value_input(self):
        self.learning.existing["kanada"] = [{
            "finding_id": "known",
            "topic": "bearing fault",
            "claim": "known verified pattern",
            "confidence": 0.95,
            "learned_at": 10,
            "unresolved": False,
        }]
        out = self.bot.plan_learning(
            source="pc",
            topic="bearing fault",
            content="bearing fault",
            confidence=0.95,
            novelty=0.0,
            quality=0.5,
            importance=0.2,
        )
        self.assertFalse(out["should_learn"])
        self.assertEqual(out["next_action"], "reuse_rishi_knowledge_or_discard_low_value_observation")

    def test_route_knowledge_stays_with_rishi_until_l3(self):
        out = self.bot.route_knowledge(
            source="pc",
            project="KRISHNA",
            topic="new materials observation",
            lesson="A new candidate relationship was observed.",
            evidence=[{"source_ref": "obs-1"}],
            provenance={"source_ref": "obs-1"},
            confidence=0.7,
            maturity="L1",
            evidence_status="candidate",
        )
        self.assertTrue(out["routed_to_rishi"])
        self.assertTrue(out["requires_more_learning"])
        self.assertIsNone(out["proposal"])
        self.assertEqual(len(self.learning.findings), 1)
        self.assertEqual(len(self.gyan.proposals), 0)

    def test_status_exposes_memory_intelligence_v2(self):
        self.bot.intake(
            source="pc",
            topic="software API version",
            content="API v2 is observed",
            evidence=[{"source_ref": "docs-v2"}],
            provenance={"source_ref": "docs-v2"},
            confidence=0.7,
            novelty=0.8,
            quality=0.9,
        )
        status = self.bot.status()
        self.assertEqual(status["version"], "brahma-learning-governor-v2")
        self.assertTrue(status["memory_intelligence"]["ready"])
        self.assertIn("bi_temporal_claims", status["memory_intelligence"]["features"])

    def test_gyan_qc_blocks_unprovenanced_low_maturity_memory(self):
        out = self.bot.qc_for_gyan(
            project="KRISHNA",
            topic="electronics",
            lesson="A claim without traceable evidence",
            evidence=[],
            provenance={},
            confidence=0.9,
            maturity="L1",
            evidence_status="candidate",
        )
        self.assertFalse(out["candidate_passed"])
        self.assertIsNone(out["proposal"])
        self.assertEqual(len(self.gyan.proposals), 0)
        self.assertIn("traceable provenance is required", out["reasons"])

    def test_gyan_qc_creates_candidate_proposal_but_does_not_store(self):
        out = self.bot.qc_for_gyan(
            project="KRISHNA",
            topic="electronics",
            lesson="Measured regulator behavior supports the candidate diagnosis.",
            evidence=[{"source_ref": "measurement-1"}],
            provenance={"source_ref": "measurement-1", "mission_id": "m1", "rishi_finding_id": "rf1"},
            confidence=0.74,
            maturity="L3",
            evidence_status="provisional_supported",
        )
        self.assertTrue(out["candidate_passed"])
        self.assertFalse(out["verified_for_gyan"])
        self.assertTrue(out["proposal"]["requires_user_approval"])
        self.assertFalse(out["proposal"]["stored"])

    def test_gyan_qc_marks_only_strong_l4_evidence_verified(self):
        out = self.bot.qc_for_gyan(
            project="KRISHNA",
            topic="vehicle diagnostics",
            lesson="The verified test result resolves the earlier fault hypothesis.",
            evidence=[{"source_ref": "test-verified"}],
            provenance={
                "source_ref": "test-verified", "claim_id": "c1",
                "researching_rishi": "kanada",
                "verification_agent": "gautama",
                "compiler": "veda-vyasa",
            },
            confidence=0.92,
            maturity="L4",
            evidence_status="verified",
            unresolved_contradictions=0,
        )
        self.assertTrue(out["candidate_passed"])
        self.assertTrue(out["verified_for_gyan"])
        self.assertTrue(out["proposal"]["verified"])
        self.assertEqual(out["proposal"]["provenance"]["brahma_qc_version"], self.bot.VERSION)


if __name__ == "__main__":
    unittest.main()
