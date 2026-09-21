import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ArchitectureContracts(unittest.TestCase):
    def text(self,p):return (ROOT/p).read_text(encoding="utf-8")
    def test_gyan_brain_identity(self):
        html=self.text("core/web_validation.html")
        self.assertIn("🧠",html); self.assertIn("Gyan-Bhandar",html)
    def test_commitment_recovery(self):
        o=self.text("core/krishna_core/orchestrator.py"); s=self.text("core/krishna_core/server.py")
        self.assertIn("resume_unfinished_work",o);self.assertIn("/api/commitments/resume",s)
    def test_kabach_project_boundary(self):
        k=self.text("core/krishna_core/kabach.py");s=self.text("core/krishna_core/server.py")
        for x in ("egress_default_deny","secret_in_payload","protect_project","gate_external_evidence"):self.assertIn(x,k)
        self.assertIn("/api/kabach/projects",s)
    def test_model_pool(self):
        r=self.text("core/krishna_core/router.py")
        for x in ("openai","anthropic","gemini","xai","openrouter","ollama"):self.assertIn(x,r)
        self.assertIn("coding_plan",r)
    def test_factory_organization_contract(self):
        sf=self.text("core/krishna_core/software_factory.py");o=self.text("core/krishna_core/orchestrator.py");s=self.text("core/krishna_core/server.py")
        for x in ("worker_request","test_plan","route_defect","suggested_worker_count","actual timestamps"):self.assertIn(x,sf)
        for x in ("EphemeralWorkerRuntime","testing_lead_live_verify","gyan_bhandar.store"):self.assertIn(x,o)
        for x in ("/api/software-factory/hr","/api/software-factory/test-plan","/api/software-factory/testing-lead/verify"):self.assertIn(x,s)
    def test_ephemeral_worker_contract(self):
        e=self.text("core/krishna_core/ephemeral_workers.py")
        for x in ("KRISHNA approval required","ThreadPoolExecutor","destroyed","max_workers"):self.assertIn(x,e)
    def test_browser_testing_lead_contract(self):
        b=self.text("core/krishna_core/browser_operator.py")
        self.assertIn("exhaustive_clickthrough",b);self.assertIn("controls_checked",b)
    def test_garuda_security_delegation(self):
        o=self.text("core/krishna_core/orchestrator.py")
        self.assertIn("kabach_security_research",o);self.assertIn("self.garuda.scout",o)

    def test_e_drive_reconciliation_contract(self):
        root=Path(__file__).resolve().parents[1]
        audit=(root/"scripts"/"AUDIT_KRISHNA_E_DRIVE.ps1").read_text(encoding="utf-8")
        integrations=(root/"core"/"krishna_core"/"integrations.py").read_text(encoding="utf-8")
        media=(root/"core"/"krishna_core"/"media_adapter.py").read_text(encoding="utf-8")
        self.assertIn("E:\\AI-Tools\\codebase-memory-mcp\\codebase-memory-mcp.exe",audit)
        self.assertIn("E:/AI-Tools/codebase-memory-mcp/codebase-memory-mcp.exe",integrations)
        self.assertIn("E:/AI-Tools/OpenMontage",media)
        self.assertIn("OPENMONTAGE_CMD",media)
        self.assertIn("MOBILE_RUNTIME_DUALITY",audit)

    def test_runtime_acceptance_is_a_deploy_gate(self):
        root=Path(__file__).resolve().parents[1]
        accept=(root/"scripts"/"ACCEPT_KRISHNA_RUNTIME.ps1").read_text(encoding="utf-8")
        deploy=(root/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        for token in (
            "/api/runtime/integrity","/api/narad/status","/api/intelligence/status",
            "/api/kabach/projects","/api/garudanetra/session/start",
            "/api/ui-guardian/evaluate","/api/gyan-bhandar/propose",
            "release_ready","AUDIT_KRISHNA_E_DRIVE.ps1",
        ):
            self.assertIn(token,accept)
        self.assertIn("ACCEPT_KRISHNA_RUNTIME.ps1",deploy)
        self.assertIn("refusing final start",deploy)

    def test_missed_additions_are_release_contracts(self):
        root=Path(__file__).resolve().parents[1]
        server=self.text("core/krishna_core/server.py")
        requirements=self.text("core/requirements/krishna_chat_requirements.json")
        for module in ("secure_vault.py","model_gateway.py","vision_adapter.py","native_voice.py","remote_access.py","wearable_bridge.py","model_memory_governor.py"):
            self.assertTrue((root/"core"/"krishna_core"/module).is_file(),module)
        for token in ("windows_dpapi_secret_vault","encrypted_free_only_model_gateway","local_attachment_vision_reasoning",
                      "openwakeword_krishna_wake_service","private_overlay_remote_access_policy",
                      "crash_loop_backoff_quarantine","wearable_bridge_verified_capabilities"):
            self.assertIn(token,server)
        for token in ("public Internet","Protected and archive","Free-only model gateway","Private + Task Memory",
                      "AI4Bharat","raw shell","vendor camera/display"):
            self.assertIn(token,requirements)
        guardian=self.text("scripts/KRISHNA_GUARDIAN.ps1")
        for token in ("CORE_QUARANTINED","RESTART_SCHEDULED","MaxCrashes","CrashWindowSeconds"):self.assertIn(token,guardian)

if __name__=="__main__":unittest.main()
