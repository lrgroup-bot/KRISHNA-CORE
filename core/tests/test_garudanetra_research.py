import tempfile
import unittest
from pathlib import Path

from krishna_core.garudanetra_research import GarudanetraResearchFabric


class GarudanetraResearchFabricTests(unittest.TestCase):
    def test_mission_builds_specialist_scout_targets(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=GarudanetraResearchFabric(Path(td))
            row=fabric.create_mission({"question":"Can acoustic stimulation change a measurable cell response?","requested_by":"rishi:kanada"})
            self.assertEqual(row["version"],"garudanetra-research-fabric-v2")
            self.assertEqual(set(row["scouts"]),{"papers","github","patents","datasets","standards","contradictions"})
            self.assertEqual(len(row["targets"]),6)
            self.assertTrue(all(x["mode"]=="task_memory" for x in row["targets"]))

    def test_evidence_keeps_contradictions_visible(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=GarudanetraResearchFabric(Path(td))
            row=fabric.create_mission({"question":"Does intervention X improve outcome Y?"})
            mid=row["mission_id"]
            fabric.ingest(mid,{
                "source_kind":"paper","url":"https://example.org/a?token=secret",
                "claim":"Intervention X improves outcome Y","claim_key":"x->y",
                "stance":"support","quality":0.9,
            })
            fabric.ingest(mid,{
                "source_kind":"replication","url":"https://example.org/b",
                "claim":"Intervention X does not improve outcome Y","claim_key":"x->y",
                "stance":"contradict","quality":0.8,
            })
            result=fabric.analyze(mid)
            self.assertEqual(result["unresolved_contradictions"],1)
            self.assertEqual(result["supporting"],1)
            self.assertEqual(result["contradicting"],1)
            saved=fabric.mission(mid)
            self.assertIn("REDACTED",saved["evidence"][0]["url"])
            self.assertNotIn("secret",saved["evidence"][0]["url"])

    def test_persisted_evidence_redacts_credentials_with_kabach_policy(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=GarudanetraResearchFabric(Path(td))
            row=fabric.create_mission({"question":"Inspect sourced evidence safely"})
            item=fabric.ingest(row["mission_id"],{
                "claim":"Result observed; password=supersecretvalue",
                "claim_key":"token=verysecretvalue",
                "title":"Authorization: Bearer abcdefghijklmnop",
                "excerpt":"api_key=abcdef1234567890 and bearer xyzxyzxyzxyzxyz",
                "source_date":"token=datedsecret",
                "url":"https://example.org/?token=querysecret&safe=yes",
                "stance":"neutral",
            })
            rendered=str(item).lower()
            for secret in ("supersecretvalue","verysecretvalue","abcdefghijklmnop",
                           "abcdef1234567890","xyzxyzxyzxyzxyz","datedsecret","querysecret"):
                self.assertNotIn(secret,rendered)
            self.assertIn("redacted",rendered)

    def test_handoff_preserves_candidate_state_for_lab_bot(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=GarudanetraResearchFabric(Path(td))
            row=fabric.create_mission({"question":"Test a measurable physical hypothesis"})
            mid=row["mission_id"]
            fabric.ingest(mid,{
                "claim":"Measured response changes under condition A",
                "claim_key":"response-a","stance":"support","quality":0.7,
            })
            package=fabric.handoff(mid,"lab_bot")
            self.assertEqual(package["target"],"lab_bot")
            self.assertTrue(package["requires_independent_verification"])
            self.assertIn("controlled experiment",package["next_step"])

    def test_distilled_skill_requires_owner_approval(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=GarudanetraResearchFabric(Path(td))
            candidate=fabric.propose_skill(
                "research.acoustic.replication",
                "Find acoustic replication evidence",
                "Search independent replication evidence before promoting a claim.",
                "mission-1",
            )
            with self.assertRaises(PermissionError):
                fabric.promote_skill(candidate,approved=False)
            row=fabric.promote_skill(candidate,approved=True)
            self.assertEqual(row["origin"],"distilled")
            self.assertEqual(row["stage"],"new")

    def test_scout_duplicate_and_circuit_breaker(self):
        calls=[]
        def factory(project,url,mode):
            calls.append((project,url,mode))
            return {"session_id":"session-"+str(len(calls)),"state":"STARTING"}
        with tempfile.TemporaryDirectory() as td:
            fabric=GarudanetraResearchFabric(Path(td),session_factory=factory)
            row=fabric.create_mission({"question":"Find strong replication evidence","scouts":["papers"]})
            mid=row["mission_id"]
            fabric.launch_scout(mid,"papers")
            with self.assertRaises(RuntimeError):
                fabric.launch_scout(mid,"papers")

            mission=fabric._load_mission(mid)
            mission["sessions"][-1]["started_at"]-=20
            fabric._save_mission(mission)
            fabric.launch_scout(mid,"papers")

            mission=fabric._load_mission(mid)
            mission["sessions"][-1]["started_at"]-=20
            fabric._save_mission(mission)
            fabric.launch_scout(mid,"papers")

            mission=fabric._load_mission(mid)
            mission["sessions"][-1]["started_at"]-=20
            fabric._save_mission(mission)
            with self.assertRaises(RuntimeError):
                fabric.launch_scout(mid,"papers")

    def test_status_keeps_playwright_as_authority(self):
        with tempfile.TemporaryDirectory() as td:
            status=GarudanetraResearchFabric(Path(td)).status()
            self.assertEqual(status["canonical_browser"],"playwright")
            self.assertTrue(status["policy"]["playwright_remains_canonical"])
            self.assertTrue(status["policy"]["jetbot_is_not_a_competing_authority"])
            self.assertGreaterEqual(len(status["skills"]),8)


if __name__=="__main__":
    unittest.main()
