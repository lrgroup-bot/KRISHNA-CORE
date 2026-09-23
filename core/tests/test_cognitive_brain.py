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

    def test_graph_survives_restart(self):
        self.brain.ingest_research("Atom",related_concepts=["Molecule"],track="modern_science")
        reloaded=KrishnaCognitiveBrain(Path(self.tmp.name)/"brain",memory=self.memory)
        result=reloaded.activate("Molecule",depth=1)
        names=[x["name"] for x in result["activated"]]
        self.assertIn("Atom",names)
        self.assertEqual(reloaded.status()["relationships"],1)


if __name__=="__main__":
    unittest.main()
