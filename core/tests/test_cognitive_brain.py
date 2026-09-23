import tempfile
import unittest
from pathlib import Path

from krishna_core.cognitive_brain import KrishnaCognitiveBrain


class FakeGyan:
    def __init__(self, rows=None):
        self.rows = rows or []

    def recall(self, project, topic=None, limit=50, verified_only=False, memory_kind=None, include_superseded=False):
        rows = list(self.rows)
        if verified_only:
            rows = [x for x in rows if x.get("status") == "verified"]
        if memory_kind:
            rows = [x for x in rows if x.get("memory_kind") == memory_kind]
        return rows[:limit]


class CognitiveBrainTests(unittest.TestCase):
    def test_anu_activation_reaches_paramanu_atom_and_molecule(self):
        with tempfile.TemporaryDirectory() as td:
            brain = KrishnaCognitiveBrain(Path(td))
            out = brain.activate("anu", depth=3)
            names = {x["name"].lower() for x in out["concepts"]}
            self.assertIn("anu", names)
            self.assertIn("paramanu", names)
            self.assertIn("atom", names)
            self.assertIn("molecule", names)

    def test_paramanu_and_molecule_queries_reuse_same_neighborhood(self):
        with tempfile.TemporaryDirectory() as td:
            brain = KrishnaCognitiveBrain(Path(td))
            p = {x.lower() for x in brain.related_terms("paramanu", depth=2)}
            m = {x.lower() for x in brain.related_terms("molecule", depth=2)}
            self.assertIn("anu", p)
            self.assertIn("atom", p)
            self.assertIn("atom", m)
            self.assertTrue("anu" in m or "paramanu" in m)

    def test_classical_and_modern_tracks_cannot_be_silently_equated(self):
        with tempfile.TemporaryDirectory() as td:
            brain = KrishnaCognitiveBrain(Path(td))
            with self.assertRaises(ValueError):
                brain.link("Anu", "Atom", "same_as", confidence=1.0)

    def test_query_expansion_adds_associated_concepts(self):
        with tempfile.TemporaryDirectory() as td:
            brain = KrishnaCognitiveBrain(Path(td))
            expanded = brain.expand_query("Explain anu")
            self.assertIn("ASSOCIATED CONCEPTS:", expanded)
            self.assertIn("Atom", expanded)
            self.assertIn("Paramanu", expanded)

    def test_activation_plan_surfaces_only_missing_or_weak_branches(self):
        rows = [
            {
                "topic": "Atom and atomic structure",
                "lesson": "Verified atomic evidence record.",
                "status": "verified",
                "confidence": 0.95,
                "memory_kind": "semantic",
            },
            {
                "topic": "Molecule and molecular structure",
                "lesson": "Verified molecule evidence record.",
                "status": "verified",
                "confidence": 0.95,
                "memory_kind": "semantic",
            },
        ]
        with tempfile.TemporaryDirectory() as td:
            brain = KrishnaCognitiveBrain(Path(td), FakeGyan(rows))
            plan = brain.activation_plan("KRISHNA", "anu")
            by_name = {x["name"]: x for x in plan["coverage"]}
            self.assertEqual(by_name["Atom"]["status"], "covered")
            self.assertEqual(by_name["Molecule"]["status"], "covered")
            gaps = {x["name"] for x in plan["knowledge_gaps"]}
            self.assertIn("Anu", gaps)
            self.assertIn("Paramanu", gaps)
            self.assertEqual(
                {x["suggested_rishi"] for x in plan["knowledge_gaps"]},
                {"Kanada"},
            )

    def test_dynamic_concepts_persist_and_are_reloaded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = KrishnaCognitiveBrain(root)
            first.learn_concept("Electron", track="modern_science")
            first.link("Atom", "Electron", "has_constituent", confidence=0.9)
            second = KrishnaCognitiveBrain(root)
            names = {x["name"] for x in second.neighbors("Atom", depth=1)}
            self.assertIn("Electron", names)
            self.assertGreaterEqual(second.status()["concept_count"], 5)


if __name__ == "__main__":
    unittest.main()
