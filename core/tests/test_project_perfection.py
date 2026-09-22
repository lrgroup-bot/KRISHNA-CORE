import unittest

from krishna_core.project_perfection import (
    CompletionProof, DeadlineHR, ElementGeometry, GateEvidence, ImmuneMemory,
    ProjectPerfectionLoop, REQUIRED_RELEASE_GATES, UIGeometryVerifier, WorkItem,
)


class ProjectPerfectionTests(unittest.TestCase):
    def test_hr_scales_parallel_work_to_deadline(self):
        plan = DeadlineHR().plan([
            WorkItem("a", "frontend", 80),
            WorkItem("b", "backend", 80),
            WorkItem("c", "integration", 10, parallelizable=False),
        ], deadline_minutes=60, max_workers=8)
        self.assertGreaterEqual(plan.recommended_workers, 4)
        self.assertLessEqual(plan.predicted_minutes, 60)

    def test_geometry_finds_overflow(self):
        findings = UIGeometryVerifier().inspect([
            ElementGeometry("#submit", 380, 10, 40, 30),
        ], 390, 844)
        self.assertEqual(findings[0]["type"], "viewport_overflow")

    def test_bug_cannot_be_immunized_without_test(self):
        memory = ImmuneMemory()
        with self.assertRaises(ValueError):
            memory.immunize("demo", "390px", "fixed width", "", "fixed")

    def test_completion_rejects_missing_gate(self):
        proof = CompletionProof()
        gates = [GateEvidence(name, True, ["ok"]) for name in REQUIRED_RELEASE_GATES[:-1]]
        cert = proof.certify("demo", "abc", gates)
        self.assertFalse(cert["passed"])
        self.assertIn(REQUIRED_RELEASE_GATES[-1], cert["missing_gates"])

    def test_completion_passes_only_all_gates(self):
        proof = CompletionProof()
        gates = [GateEvidence(name, True, ["verified"]) for name in REQUIRED_RELEASE_GATES]
        cert = proof.certify("demo", "abc", gates, mutation_detection=0.97)
        self.assertTrue(cert["passed"])
        self.assertEqual(cert["verdict"], "RELEASE_GATES_PASSED")

    def test_discovery_contract_has_post_package_retest(self):
        contract = ProjectPerfectionLoop.discovery_contract()
        self.assertTrue(contract["post_package_retest"])
        self.assertIn(390, contract["viewports"])
        self.assertIn("api_500", contract["adversarial"])


if __name__ == "__main__":
    unittest.main()
