import os
import unittest
from pathlib import Path


def repository_root():
    configured=str(os.environ.get("KRISHNA_SOURCE_ROOT") or "").strip()
    return Path(configured).resolve() if configured else Path(__file__).resolve().parents[2]


class DeploymentRuntimeContractTests(unittest.TestCase):
    def test_deployed_core_tests_resolve_repo_only_contracts_from_source(self):
        root=repository_root()
        deploy=(root/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        self.assertIn('$env:KRISHNA_SOURCE_ROOT=$Source',deploy)
        self.assertIn('finally{',deploy)
        self.assertIn('Remove-Item Env:KRISHNA_SOURCE_ROOT',deploy)

    def test_avatar_prepare_does_not_pass_boolean_values_through_powershell_file(self):
        root=repository_root()
        deploy=(root/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        line=next(x for x in deploy.splitlines() if "-File $avatarPrepare" in x)
        self.assertNotIn("-TryBodyRig",line)
        self.assertNotIn("-InstallRigTools",line)
        self.assertIn("-RuntimeRoot $Runtime",line)
        self.assertIn("-SourceRoot $Source",line)

    def test_acceptance_uses_current_shishya_tree_contract_not_legacy_four_worker_cap(self):
        root=repository_root()
        accept=(root/"scripts"/"ACCEPT_KRISHNA_RUNTIME.ps1").read_text(encoding="utf-8")
        self.assertNotIn("requested_count -le 4",accept)
        self.assertIn("$shishyaRequested -le 32",accept)
        self.assertIn("$shishyaConcurrent -ge 1 -and $shishyaConcurrent -le 8",accept)
        self.assertIn("$shishyaTreeNodes -ge 1 -and $shishyaTreeNodes -le 256",accept)
        self.assertIn('$shishyaResult.retention_policy -eq "findings_and_provenance_only"',accept)
        self.assertIn('$shishyaResult.destruction_policy -match "retire every Shishya"',accept)

    def test_acceptance_exercises_brahma_qc_before_gyan_approval(self):
        root=repository_root()
        accept=(root/"scripts"/"ACCEPT_KRISHNA_RUNTIME.ps1").read_text(encoding="utf-8")
        self.assertIn('verification_agent="gautama"',accept)
        self.assertIn('compiler="veda-vyasa"',accept)
        self.assertIn('maturity="L4"',accept)
        self.assertIn('evidence_status="verified"',accept)
        self.assertIn('$proposal.brahma.verified_for_gyan',accept)
        self.assertNotIn('source="runtime_acceptance";verified=$true',accept)

    def test_runtime_acceptance_requires_master_truth_and_unified_hawkeye(self):
        root=repository_root()
        accept=(root/"scripts"/"ACCEPT_KRISHNA_RUNTIME.ps1").read_text(encoding="utf-8")
        self.assertIn('"/api/architecture/truth"',accept)
        self.assertIn('"hawkeye-coordinator-v1"',accept)
        self.assertIn('"perception","physio","behavior","temporal","diagnostic","reasoner"',accept)
        self.assertIn("sensitive_input_guard.return_secret_value",accept)
        self.assertIn("face_recognition.unknown_person_identity",accept)

    def test_one_command_architecture_audit_exists(self):
        root=repository_root()
        audit=(root/"scripts"/"AUDIT_KRISHNA_ARCHITECTURE.ps1").read_text(encoding="utf-8")
        self.assertIn("ArchitectureTruthAudit",audit)
        self.assertIn("Missing evidence paths",audit)
        self.assertIn("Orphan review candidates",audit)

    def test_repo_contract_tests_honor_authoritative_source_root(self):
        root=repository_root()
        audit=(root/"core"/"tests"/"test_project_audit.py").read_text(encoding="utf-8")
        perfection=(root/"core"/"tests"/"test_project_perfection_orchestrator_contract.py").read_text(encoding="utf-8")
        self.assertIn("KRISHNA_SOURCE_ROOT",audit)
        self.assertIn("KRISHNA_SOURCE_ROOT",perfection)


if __name__=="__main__":
    unittest.main()
