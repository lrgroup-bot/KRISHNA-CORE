import tempfile
import unittest
from pathlib import Path

from krishna_core.cognitive_brain import KrishnaCognitiveBrain


class MemoryStub:
    def __init__(self):
        self.events=[]

    def audit(self, action, status, detail):
        self.events.append((action,status,detail))


class CognitiveBrainTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.memory=MemoryStub()
        self.brain=KrishnaCognitiveBrain(Path(self.tmp.name)/"brain",memory=self.memory)

    def tearDown(self):
        self.tmp.cleanup()

    def test_associative_activation_reaches_connected_concepts(self):
        self.brain.ingest_research(
            "Anu",
            track="vedic_classical",
            confidence=.82,
            maturity="L8",
            evidence_status="verified",
            related_concepts=[
                {"name":"Paramanu","track":"vedic_classical","relation":"related_to","weight":.9},
                {"name":"Atom","track":"modern_science","relation":"compared_with","weight":.8},
            ],
            relationships=[
                {
                    "source":"Atom","target":"Molecule",
                    "source_track":"modern_science","target_track":"modern_science",
                    "relation":"combines_to_form","weight":.95,
                }
            ],
            provenance={"mission_id":"m1","claim_id":"c1"},
            rishi_id="kanada",
        )
        result=self.brain.activate("Molecule",depth=2,limit=20)
        names=[x["name"] for x in result["activated"]]
        self.assertFalse(result["knowledge_gap"])
        self.assertIn("Molecule",names)
        self.assertIn("Atom",names)
        self.assertIn("Anu",names)

        anu=self.brain._get("Anu")
        atom=self.brain._get("Atom")
        self.assertIn("vedic_classical",anu["tracks"])
        self.assertNotIn("modern_science",anu["tracks"])
        self.assertIn("modern_science",atom["tracks"])

    def test_cross_track_equivalence_is_rejected(self):
        self.brain.learn_concept("Anu",track="vedic_classical")
        self.brain.learn_concept("Atom",track="modern_science")
        with self.assertRaises(ValueError):
            self.brain.link(
                "Anu","Atom",
                relation="equivalent_to",
                source_track="vedic_classical",
                target_track="modern_science",
            )
        compared=self.brain.link(
            "Anu","Atom",
            relation="compared_with",
            source_track="vedic_classical",
            target_track="modern_science",
        )
        self.assertTrue(compared["cross_track_comparison"])

    def test_unknown_concept_becomes_explicit_gap(self):
        result=self.brain.activate("Unseen concept",depth=3)
        self.assertTrue(result["knowledge_gap"])
        self.assertEqual(result["activated"],[])

    def test_sensitive_provenance_is_redacted_before_persistence(self):
        self.brain.learn_concept(
            "Secure concept",
            provenance={"note":"token=abcdefghijklmnopqrstuvwxyz","password":"supersecret"},
        )
        raw=(Path(self.tmp.name)/"brain"/"concept-graph.json").read_text(encoding="utf-8")
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz",raw)
        self.assertNotIn("supersecret",raw)
        self.assertIn("[REDACTED]",raw)


    def test_c6_structural_analogy_is_candidate_not_equivalence(self):
        self.brain.ingest_research(
            "Atomic system",
            track="modern_science",
            related_concepts=[
                {"name":"Nucleus","track":"modern_science","relation":"contains","weight":.9},
                {"name":"Electron cloud","track":"modern_science","relation":"contains","weight":.9},
            ],
        )
        self.brain.ingest_research(
            "Organization",
            track="operational",
            related_concepts=[
                {"name":"Core team","track":"operational","relation":"contains","weight":.9},
                {"name":"Support team","track":"operational","relation":"contains","weight":.9},
            ],
        )
        out=self.brain.form_analogies("Atomic system",min_score=.2)
        match=next(x for x in out["analogies"] if x["target"]=="Organization")
        self.assertEqual(match["status"],"candidate_analogy")
        self.assertIn("contains",match["shared_relations"])
        self.assertTrue(match["cross_domain"])
        self.assertIn("not evidence",out["policy"])

    def test_contradictions_drive_curiosity_questions_not_answers(self):
        out=self.brain.curiosity_from_contradictions([{
            "contradiction_id":"cx1","status":"open","topic":"bearing fault",
            "claim_a_text":"outer-race damage causes the vibration",
            "claim_b_text":"loose mounting causes the vibration",
        }])
        self.assertEqual(out["count"],1)
        q=out["questions"][0]
        self.assertEqual(q["status"],"open_research_question")
        self.assertIn("independent evidence",q["question"])
        self.assertIn("does not choose a winner",out["policy"])

    def test_episodic_repetition_creates_semantic_candidate_only(self):
        episodes=[
            {
                "topic":"bearing observation","lesson":"periodic vibration after warm-up",
                "confidence":.7,"fingerprint":"e1","evidence":[{"source_ref":"m1"}],
                "provenance":{"observation_id":"o1"},
            },
            {
                "topic":"bearing observation","lesson":"periodic vibration after warm-up",
                "confidence":.8,"fingerprint":"e2","evidence":[{"source_ref":"m2"}],
                "provenance":{"observation_id":"o2"},
            },
        ]
        out=self.brain.consolidate_episodes(episodes,min_occurrences=2)
        self.assertEqual(len(out["semantic_candidates"]),1)
        item=out["semantic_candidates"][0]
        self.assertEqual(item["memory_kind"],"semantic")
        self.assertEqual(item["source_memory_kind"],"episodic")
        self.assertTrue(item["requires_brahma_qc"])
        self.assertTrue(item["requires_gyan_approval"])

    def test_controlled_forgetting_is_reversible_and_protects_evidence(self):
        orphan=self.brain.learn_concept("Temporary orphan",confidence=.05)
        protected=self.brain.learn_concept(
            "Verified knowledge",confidence=.95,evidence_status="verified",
            provenance={"source_ref":"paper-1"},
        )
        old=1.0
        with self.brain.lock:
            self.brain.state["concepts"][orphan["concept_id"]]["updated_at"]=old
            self.brain.state["concepts"][protected["concept_id"]]["updated_at"]=old
            self.brain._save()
        out=self.brain.controlled_forget(
            now=200*86400.0,candidate_ttl_days=30,apply=True
        )
        dormant={x["name"] for x in out["concepts_dormant_candidate"]}
        self.assertIn("Temporary orphan",dormant)
        self.assertNotIn("Verified knowledge",dormant)
        self.assertTrue(self.brain.state["concepts"][orphan["concept_id"]]["dormant"])
        self.assertFalse(self.brain.state["concepts"][protected["concept_id"]].get("dormant",False))
        self.assertIsNone(self.brain.resolve("Temporary orphan")["concept_id"])
        revived=self.brain.learn_concept("Temporary orphan",confidence=.4)
        self.assertFalse(revived["dormant"])

    def test_c7_cross_domain_hypothesis_is_unverified_and_falsifiable(self):
        self.brain.ingest_research(
            "System behavior",
            track="general",
            related_concepts=[
                {"name":"Atom","track":"modern_science","relation":"exhibits_pattern","weight":.9},
                {"name":"Gearbox","track":"engineering","relation":"exhibits_pattern","weight":.9},
            ],
        )
        out=self.brain.generate_hypotheses("System behavior",depth=2,limit=10)
        self.assertGreaterEqual(out["count"],1)
        cross=next(
            x for x in out["hypotheses"]
            if {x["left"],x["right"]}=={"Atom","Gearbox"}
        )
        self.assertEqual(cross["status"],"unverified_hypothesis")
        self.assertIn("falsify",cross["question"])
        self.assertIn("not learned facts",out["policy"])
        self.assertEqual(self.brain.status()["progressive_cognition_level"],"C7")

    def test_graph_survives_restart(self):
        self.brain.ingest_research("Atom",related_concepts=["Molecule"],track="modern_science")
        reloaded=KrishnaCognitiveBrain(Path(self.tmp.name)/"brain",memory=self.memory)
        result=reloaded.activate("Molecule",depth=1)
        names=[x["name"] for x in result["activated"]]
        self.assertIn("Atom",names)
        self.assertEqual(reloaded.status()["relationships"],1)


if __name__=="__main__":
    unittest.main()
