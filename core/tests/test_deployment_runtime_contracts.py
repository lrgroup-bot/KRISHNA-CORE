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

    def test_source_tests_use_isolated_runtime_and_must_leave_git_clean(self):
        root=repository_root()
        deploy=(root/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        self.assertIn('workspace\\source-tests',deploy)
        self.assertIn('$env:KRISHNA_RUNTIME_ROOT=$sourceTestRuntime',deploy)
        self.assertIn('$env:KRISHNA_DB=Join-Path $sourceTestRuntime "krishna_core.db"',deploy)
        self.assertIn('$env:KRISHNA_SOURCE_ROOT=$Source',deploy)
        self.assertIn('SOURCE TESTS DIRTY THE REPOSITORY',deploy)
        self.assertIn('Remove-Item -Recurse -Force $sourceTestRuntime',deploy)

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

    def test_runtime_acceptance_compares_live_truth_versions_instead_of_hardcoding_ledger_version(self):
        root=repository_root()
        accept=(root/"scripts"/"ACCEPT_KRISHNA_RUNTIME.ps1").read_text(encoding="utf-8")
        self.assertIn('$truth.requirements.version -eq [string]$requirements.version',accept)
        self.assertIn('$truth.requirements.schema -eq 2',accept)
        self.assertIn('$truthEvidenceMissing.Count -eq 0',accept)
        self.assertIn('$truthInvalidStatuses.Count -eq 0',accept)
        self.assertNotIn('2026-09-23-master-product-truth-v2',accept)

    def test_runtime_acceptance_surfaces_duplicate_orphan_and_source_tree_review_candidates(self):
        root=repository_root()
        accept=(root/"scripts"/"ACCEPT_KRISHNA_RUNTIME.ps1").read_text(encoding="utf-8")
        self.assertIn('"Architecture duplicate/orphan review"',accept)
        self.assertIn('$truth.summary.duplicate_basenames',accept)
        self.assertIn('$truth.summary.identical_content_groups',accept)
        self.assertIn('$truth.summary.orphan_candidates',accept)
        self.assertIn('$truth.summary.source_tree_missing_current_modules',accept)
        self.assertIn('no automatic deletion',accept)

    def test_one_command_architecture_audit_exists(self):
        root=repository_root()
        audit=(root/"scripts"/"AUDIT_KRISHNA_ARCHITECTURE.ps1").read_text(encoding="utf-8")
        self.assertIn("ArchitectureTruthAudit",audit)
        self.assertIn("Missing evidence paths",audit)
        self.assertIn("Orphan review candidates",audit)

    def test_verified_deploy_starts_persistent_guardian_and_waits_for_health(self):
        root=repository_root()
        deploy=(root/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        self.assertIn('KRISHNA_GUARDIAN.ps1',deploy)
        self.assertIn('Start-Process -FilePath "powershell.exe" -ArgumentList $guardianArgs',deploy)
        self.assertIn('http://127.0.0.1:8766/health',deploy)
        self.assertIn('newly launched runtime generation did not become healthy on 8766',deploy)
        self.assertNotIn('& "$Runtime\\scripts\\START_KRISHNA.ps1"',deploy)

    def test_guardian_records_guardian_and_core_pid_plus_runtime_logs(self):
        root=repository_root()
        guardian=(root/"scripts"/"KRISHNA_GUARDIAN.ps1").read_text(encoding="utf-8")
        self.assertIn('"guardian.pid"',guardian)
        self.assertIn('guardian_pid=$PID',guardian)
        self.assertIn('core_pid=$p.Id',guardian)
        self.assertIn('core-runtime.stdout.log',guardian)
        self.assertIn('core-runtime.stderr.log',guardian)
        self.assertIn('$p.WaitForExit()',guardian)
        self.assertIn('ALREADY_RUNNING',guardian)

    def test_guardian_launch_quotes_runtime_paths_and_captures_bootstrap_logs(self):
        root=repository_root()
        deploy=(root/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        guardian=(root/"scripts"/"KRISHNA_GUARDIAN.ps1").read_text(encoding="utf-8")
        self.assertIn('$guardianArgs=\'-NoProfile -ExecutionPolicy Bypass -File "'+'$guardian+',deploy)
        self.assertIn('-RuntimeRoot "'+'$Runtime+',deploy)
        self.assertIn('-SourceRoot "'+'$Source+',deploy)
        self.assertIn("guardian-bootstrap.stdout.log",deploy)
        self.assertIn("guardian-bootstrap.stderr.log",deploy)
        self.assertIn("-RedirectStandardOutput $guardianStdout",deploy)
        self.assertIn("-RedirectStandardError $guardianStderr",deploy)
        self.assertIn('$coreArgs=\'-NoProfile -ExecutionPolicy Bypass -File "'+'$startScript+',guardian)
        self.assertIn('-KrishnaRoot "'+'$RuntimeRoot+',guardian)
        self.assertIn('-SourceRoot "'+'$SourceRoot+',guardian)
        self.assertIn('Start-Process -FilePath "powershell.exe" -ArgumentList $coreArgs',guardian)

    def test_generation_handoff_terminates_verified_core_process_tree(self):
        root=repository_root()
        deploy=(root/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        self.assertIn("taskkill.exe /PID $oldCorePid /T /F",deploy)
        self.assertIn("Port 8766 remains occupied after KRISHNA generation handoff",deploy)
        self.assertIn("Refusing to kill an unverified listener",deploy)

    def test_verified_deploy_takes_over_previous_guardian_generation_safely(self):
        root=repository_root()
        deploy=(root/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        guardian=(root/"scripts"/"KRISHNA_GUARDIAN.ps1").read_text(encoding="utf-8")
        self.assertIn("Stop-ExistingKrishnaGuardian",deploy)
        self.assertIn('Get-KrishnaProcess $oldGuardianPid "KRISHNA_GUARDIAN.ps1"',deploy)
        self.assertIn('Get-KrishnaProcess $oldCorePid "START_KRISHNA.ps1"',deploy)
        self.assertIn('"DEPLOY_GENERATION_HANDOFF"|Set-Content',deploy)
        self.assertIn("taskkill.exe /PID $oldCorePid /T /F",deploy)
        self.assertIn("STALE_GUARDIAN_PID",guardian)
        self.assertIn('existingCmd -like "*KRISHNA_GUARDIAN.ps1*"',guardian)

    def test_deploy_health_is_bound_to_new_guardian_generation(self):
        root=repository_root()
        deploy=(root/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        guardian=(root/"scripts"/"KRISHNA_GUARDIAN.ps1").read_text(encoding="utf-8")
        server=(root/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8")
        self.assertIn('$runtimeGeneration=[guid]::NewGuid().ToString("N")',deploy)
        self.assertIn('-RuntimeGeneration "\'+$runtimeGeneration+\'"',deploy)
        self.assertIn('$guardianProc.HasExited',deploy)
        self.assertIn('$health.runtime_generation -eq $runtimeGeneration',deploy)
        self.assertIn('[string]$RuntimeGeneration=""',guardian)
        self.assertIn('$env:KRISHNA_RUNTIME_GENERATION=$RuntimeGeneration',guardian)
        self.assertIn('runtime_generation=$RuntimeGeneration',guardian)
        self.assertIn('"runtime_generation": os.environ.get("KRISHNA_RUNTIME_GENERATION", "")',server)

    def test_orchestrator_architecture_truth_honors_authoritative_source_root(self):
        root=repository_root()
        orchestrator=(root/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("KRISHNA_SOURCE_ROOT")',orchestrator)
        self.assertIn("ArchitectureTruthAudit(repo_root)",orchestrator)

    def test_repo_contract_tests_honor_authoritative_source_root(self):
        root=repository_root()
        audit=(root/"core"/"tests"/"test_project_audit.py").read_text(encoding="utf-8")
        perfection=(root/"core"/"tests"/"test_project_perfection_orchestrator_contract.py").read_text(encoding="utf-8")
        self.assertIn("KRISHNA_SOURCE_ROOT",audit)
        self.assertIn("KRISHNA_SOURCE_ROOT",perfection)


if __name__=="__main__":
    unittest.main()
