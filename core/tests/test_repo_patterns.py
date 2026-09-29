import tempfile
import unittest

from krishna_core.repo_patterns import (
    AgentCheckpoint,
    AgentCheckpointLedger,
    AndroidInspectionPolicy,
    ExperimentSpec,
    LocalVoicePolicy,
    ResearchExperimentFabric,
)


class RepoPatternTests(unittest.TestCase):
    def test_checkpoint_is_persistent_and_fingerprinted(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = AgentCheckpointLedger(root)
            record = ledger.append(AgentCheckpoint(project="KRISHNA", agent="Mrityunjay", objective="repair"))
            self.assertEqual(len(record["fingerprint"]), 64)
            self.assertEqual(ledger.recent()[0]["agent"], "Mrityunjay")

    def test_research_experiment_keeps_evidence_lineage(self):
        with tempfile.TemporaryDirectory() as root:
            fabric = ResearchExperimentFabric(root)
            experiment = fabric.create(
                ExperimentSpec("Does change X improve Y?", "X improves Y", "A/B test", ("accuracy", "latency")),
                agents=("researcher", "critic", "analyst"),
            )
            result = fabric.record_result(experiment["experiment_id"], {"accepted": True}, ["run.json", "metrics.csv"])
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(result["evidence"], ["run.json", "metrics.csv"])

    def test_android_inspection_requires_authorization(self):
        self.assertFalse(AndroidInspectionPolicy.authorize(owner_authorized=False, purpose="audit", package_path="x.apk")["allowed"])
        self.assertTrue(AndroidInspectionPolicy.authorize(owner_authorized=True, purpose="audit", package_path="x.apk")["allowed"])
        self.assertFalse(AndroidInspectionPolicy.authorize(owner_authorized=True, purpose="audit", package_path="x.exe")["allowed"])

    def test_voice_clone_requires_consent_and_stays_local(self):
        denied = LocalVoicePolicy.plan(consent=False, language="Odia", operation="clone")
        allowed = LocalVoicePolicy.plan(consent=True, language="Odia", operation="clone")
        self.assertFalse(denied["allowed"])
        self.assertTrue(allowed["allowed"])
        self.assertTrue(allowed["local_first"])
        self.assertFalse(allowed["cloud_upload"])


if __name__ == "__main__":
    unittest.main()
