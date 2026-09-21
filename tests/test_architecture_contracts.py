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
    def test_garudanetra_browser_fabric_is_canonical(self):
        server=self.text("core/krishna_core/server.py")
        fabric=self.text("core/krishna_core/browser_fabric.py")
        start=self.text("scripts/START_KRISHNA.ps1")
        audit=self.text("scripts/AUDIT_KRISHNA_E_DRIVE.ps1")
        self.assertIn("GarudanetraBrowserFabric",server)
        self.assertNotIn("from .garudanetra import GarudanetraService",server)
        self.assertIn('canonical":"playwright"',fabric)
        for name in ("browser_harness","agent_browser","browsercode","opendevbrowser","rustwright","lucarne","promptwright","skyvern","rrweb","cereon_browser_operator"):
            self.assertIn(name,fabric)
        for token in ("semantic_snapshot_refs","cdp_screencast","bounded_replay","candidate_skill_learning"):
            self.assertIn(token,fabric)
        self.assertIn("PLAYWRIGHT_BROWSERS_PATH",start)
        self.assertIn("KRISHNA_BROWSER_DATA_ROOT",start)
        self.assertIn("LEGACY_BROWSER_DATA_PRESENT",audit)
        self.assertIn("LEGACY_GARUDANETRA_MODULE_PRESENT",audit)

    def test_browser_runtime_config_can_be_loaded_without_source_edits(self):
        start=self.text("scripts/START_KRISHNA.ps1")
        self.assertIn('config\\browser-runtime.ps1',start)
        self.assertIn('$browserConfig',start)
        self.assertIn('. $browserConfig',start)

    def test_agent_native_reference_layers_share_one_action_authority(self):
        root=Path(__file__).resolve().parents[1]
        orchestrator=self.text("core/krishna_core/orchestrator.py")
        server=self.text("core/krishna_core/server.py")
        web=self.text("core/web_validation.html")
        modules=(
            "shared_action_bus.py","permission_runtime.py","agent_runtime.py",
            "job_runtime.py","protocol_gateway.py","dispatch_runtime.py","sudarshan_control.py",
        )
        for module in modules:
            self.assertTrue((root/"core"/"krishna_core"/module).is_file(),module)
        for token in (
            "SharedActionBus","PermissionRuntime","AgentRuntime","JobRuntime",
            "AgentProtocolGateway","DispatchRuntime",
        ):
            self.assertIn(token,orchestrator)
        for token in (
            "/api/action-bus","/api/agents/runtime","/api/jobs/runtime",
            "/api/permissions/runtime","/api/protocols/status","/api/dispatch/status","/api/sudarshan/runtime",
        ):
            self.assertIn(token,server)
        for action in ("chat.create","chat.move","chat.rename","chat.delete","project.register",
                       "garuda.scout","garudanetra.start","garudanetra.control"):
            self.assertIn(action,orchestrator+server+web)
        self.assertIn("action.sync",server)
        self.assertIn("actionReq('garuda.scout'",web)
        self.assertIn("actionReq('garudanetra.start'",web)
        self.assertIn("actionReq('garudanetra.control'",web)
        self.assertIn("actionReq('garudanetra.upload_attachment'",web)

    def test_ui_mutation_foundation_uses_action_receipts_for_priority_surfaces(self):
        web=self.text("core/web_validation.html")
        for action in (
            "project.register","chat.create","chat.rename","chat.delete","chat.move",
            "garuda.scout","garudanetra.start","garudanetra.control","garudanetra.upload_attachment",
        ):
            self.assertIn("actionReq('"+action+"'",web)
        self.assertIn("dataset.lastActionId",web)
        self.assertIn("dataset.lastActionStatus",web)

    def test_sudarshan_narad_n8n_pattern_boundary(self):
        root=Path(__file__).resolve().parents[1]
        orchestrator=self.text("core/krishna_core/orchestrator.py")
        server=self.text("core/krishna_core/server.py")
        narad=self.text("core/krishna_core/narad/runtime.py")
        sudarshan=self.text("core/krishna_core/sudarshan_control.py")
        requirements=self.text("core/requirements/krishna_chat_requirements.json")
        for module in (
            "narad/contracts.py","narad/workflow_graph.py","narad/context.py","narad/retry.py",
            "sudarshan_control.py",
        ):
            self.assertTrue((root/"core"/"krishna_core"/module).is_file(),module)
        for token in (
            "SudarshanControlPlane","self.agi.narad.bind_sudarshan(self.sudarshan)",
            "self.agent_runtime.bind_sudarshan(self.sudarshan)",
            "self.protocols.bind_sudarshan(self.sudarshan)",
            "self.dispatcher.bind_sudarshan(self.sudarshan)",
        ):
            self.assertIn(token,orchestrator)
        for token in (
            "/api/sudarshan/runtime","/api/narad/checkpoints","/api/narad/checkpoints/resume",
        ):
            self.assertIn(token,server)
        for token in (
            "WorkflowGraph","run_with_retry","build_node_payload","resume_checkpoint",
            '"workflow_engine":"typed-dag/sudarshan"',"self.sudarshan.verify_workflow",
        ):
            self.assertIn(token,narad)
        self.assertIn("IndependentCriticVerifier",sudarshan)
        self.assertIn("n8n-style workflow patterns natively",requirements)
        self.assertIn("does not embed the n8n runtime",requirements)
        self.assertNotIn("from n8n",orchestrator+narad)
        self.assertNotIn("import n8n",orchestrator+narad)

    def test_models_workers_browser_and_developer_enter_sudarshan(self):
        orchestrator=self.text("core/krishna_core/orchestrator.py")
        router=self.text("core/krishna_core/router.py")
        server=self.text("core/krishna_core/server.py")
        web=self.text("core/web_validation.html")
        for token in (
            "self.router.bind_sudarshan(self.sudarshan)",
            '"worker.ephemeral.execute"',
            '"browser.inspect"',
            '"browser.testing_lead"',
            '"development.git.status"',
            '"development.git.commit"',
            '"development.git.push"',
            '"development.sync"',
            '"development.stage"',
            '"development.verify"',
            '"work.managed.run"',
            '"repair.shadow"',
            '"promotion.prepare"',
            '"promotion.apply"',
        ):
            self.assertIn(token,orchestrator)
        self.assertIn("self.control_plane.action(",router)
        self.assertIn('"model.complete"',router)
        self.assertIn('project=str(project or "KRISHNA")',router)
        # Public compatibility endpoints must resolve to governed Orchestrator wrappers.
        for token in (
            "orch.run_ephemeral_workers(","orch.testing_lead_live_verify(","orch.inspect_ui(",
            "orch.development_commit(","orch.development_push(","orch.development_sync(",
            "orch.development_stage(","orch.development_verify(","orch.run_managed_goal(",
            "orch.run_shadow_repair(","orch.prepare_promotion(","orch.promote_candidate(",
        ):
            self.assertIn(token,server)
        # NARAD priority UI mutation controls use action receipts directly.
        for action in (
            "narad.workflow.create","narad.workflow.promote",
            "narad.workflow.execute","narad.dead_letter.retry",
        ):
            self.assertIn("actionReq('"+action+"'",web)
        self.assertNotIn("actionReq('narad.webhook.provision'",web)

    def test_n8n_stays_external_connector_under_sudarshan(self):
        agi=self.text("core/krishna_core/agi_kernel.py")
        runtime=self.text("core/krishna_core/narad/runtime.py")
        bridge=self.text("core/krishna_core/narad/n8n_bridge.py")
        start=self.text("scripts/START_KRISHNA.ps1")
        web=self.text("core/web_validation.html")
        self.assertIn('"n8n":N8nBridge()',agi)
        self.assertIn('workflow_engine":"typed-dag/sudarshan"',runtime)
        self.assertIn('remote n8n webhook requires KRISHNA_N8N_ALLOWED_HOSTS',bridge)
        self.assertIn('config\\narad-runtime.ps1',start)
        self.assertIn('id="naradLoad"',web)
        self.assertIn('id="naradConnectorCount"',web)
        self.assertIn('id="naradN8n"',web)
        self.assertNotIn('n8n-io/n8n',agi+runtime+web)

    def test_narad_resource_gate_is_lightweight_and_bounded(self):
        gate=self.text("core/krishna_core/narad/execution_gate.py")
        self.assertIn('KRISHNA_NARAD_MAX_CONCURRENT',gate)
        self.assertIn('min(int(configured),4)',gate)
        self.assertIn('no extra worker pool',gate)
        self.assertNotIn('ThreadPoolExecutor',gate)
        self.assertNotIn('ProcessPoolExecutor',gate)

    def test_avatar_character_performance_bible_is_single_source_of_truth(self):
        avatar=self.text("core/krishna_core/avatar_fabric.py")
        server=self.text("core/krishna_core/server.py")
        web=self.text("core/web_validation.html")
        bible=self.text("docs/KRISHNA_CHARACTER_PERFORMANCE_BIBLE.md")
        for token in ("face-first","peacock feather","pitambara","Bala Krishna","Venugopala","Gita Krishna","Odissi"):
            self.assertIn(token,avatar+bible)
        for state in ("LISTENING","THINKING","SPEAKING","WISDOM","PLAYFUL","PROTECTION","FLUTE","DHYAN","SLEEPING","WAKING"):
            self.assertIn('"'+state+'"',avatar)
        self.assertIn('/api/avatar/performance',server)
        self.assertIn('state_for_activity',server)
        self.assertIn('avatarState(d.avatar_state',web)
        self.assertIn("character-bible-v1",avatar+web)
        self.assertIn('"pc"',avatar)
        self.assertIn('"mobile"',avatar)
        self.assertIn('"glass"',avatar)

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

    def test_mobile_security_and_private_remote_invariants(self):
        server=self.text("core/krishna_core/server.py")
        rpc=self.text("core/krishna_core/mobile_rpc.py")
        mobile=self.text("mobile_v3/MainActivity.java")
        requirements=self.text("core/requirements/krishna_chat_requirements.json")
        for dangerous in ("system.run","filesystem.write","credentials.read","trade.execute"):
            self.assertNotIn('"'+dangerous+'"',rpc)
        for token in ("privateCoreUrl","100&&d>=64&&d<=127","credential_sha256","pairingRequest"):
            self.assertIn(token,mobile)
        self.assertIn("public Internet",requirements)
        self.assertIn("raw shell",requirements)
        self.assertIn("/api/mobile/pair/pending",server)

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
        self.assertIn('Get-ChildItem (Join-Path $Source "scripts")',deploy)
        self.assertIn("$currentBranch=(git branch --show-current).Trim()",deploy)
        self.assertIn("provisional manifest rolled back",deploy)
        self.assertIn('state\\acceptance\\',accept)
        self.assertIn('$env:KRISHNA_DB=Join-Path $acceptanceState "krishna_core.db"',accept)
        self.assertIn('Add-Check "Acceptance harness" "FAIL"',accept)
        self.assertIn('Remove-Item -Recurse -Force $acceptanceState',accept)

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
