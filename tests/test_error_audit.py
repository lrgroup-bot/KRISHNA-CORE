import ast
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class RepositoryErrorAudit(unittest.TestCase):
    def test_all_python_sources_parse(self):
        failures=[]
        for path in ROOT.rglob("*.py"):
            if any(part in {".git",".venv","venv","node_modules"} for part in path.parts):
                continue
            try:
                ast.parse(path.read_text(encoding="utf-8-sig"),filename=str(path))
            except Exception as exc:
                failures.append(f"{path.relative_to(ROOT)}: {type(exc).__name__}: {exc}")
        self.assertEqual(failures,[],failures)

    def test_core_never_uses_shell_true(self):
        bad=[]
        for path in (ROOT/"core"/"krishna_core").rglob("*.py"):
            text=path.read_text(encoding="utf-8-sig")
            if re.search(r"shell\s*=\s*True",text):
                bad.append(str(path.relative_to(ROOT)))
        self.assertEqual(bad,[],bad)

    def test_no_stale_machine_specific_mobile_address(self):
        targets=[
            ROOT/"mobile_v3"/"MainActivity.java",
            ROOT/"mobile_v3"/"index.html",
            ROOT/"scripts"/"START_KRISHNA.ps1",
        ]
        bad=[]
        for path in targets:
            text=path.read_text(encoding="utf-8-sig")
            for token in ("192.168.0.106","C:\\Users\\godxw","C:/Users/godxw"):
                if token in text:bad.append(f"{path.relative_to(ROOT)} -> {token}")
        self.assertEqual(bad,[],bad)

    def test_sudarshan_has_no_duplicate_attributes_in_literal_tags(self):
        text=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        problems=[]
        for tag in re.findall(r"<[A-Za-z][^>]*>",text):
            attrs=[x.lower() for x in re.findall(r"\s([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=",tag)]
            dup=sorted({x for x in attrs if attrs.count(x)>1})
            if dup:problems.append((tag[:240],dup))
        self.assertEqual(problems,[],problems)

    def test_server_wiring_has_no_duplicate_import_or_singleton_lines(self):
        text=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8-sig")
        lines=[x.strip() for x in text.splitlines() if x.strip()]
        imports=[x for x in lines if x.startswith("from ") or x.startswith("import ")]
        repeated_imports=sorted({x for x in imports if imports.count(x)>1})
        self.assertEqual(repeated_imports,[],repeated_imports)
        self.assertEqual(text.count("_wearables = WearableBridge("),1)
        self.assertEqual(text.count('if path in ("/api/wearables","/api/wearables/status")'),1)
        self.assertNotIn('if path == "/api/wearables":',text)

    def test_mobile_webview_and_private_link_are_hardened(self):
        text=(ROOT/"mobile_v3"/"MainActivity.java").read_text(encoding="utf-8-sig")
        for token in (
            "setAllowFileAccessFromFileURLs(false)",
            "setAllowUniversalAccessFromFileURLs(false)",
            "MIXED_CONTENT_NEVER_ALLOW",
            "shouldOverrideUrlLoading",
            "privateCoreUrl",
            "KRISHNA_DISCOVER_V1",
            "coreBase()",
        ):
            self.assertIn(token,text)
        self.assertNotIn("192.168.0.106",text)
        self.assertIn("try(OutputStream out=c.getOutputStream())",text)
        self.assertIn("finally{c.disconnect();}",text)


    def test_part1_runtime_security_regressions_stay_fixed(self):
        server=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8-sig")
        executor=(ROOT/"core"/"krishna_core"/"executor_fabric.py").read_text(encoding="utf-8-sig")
        workers=(ROOT/"core"/"krishna_core"/"worker_fabric.py").read_text(encoding="utf-8-sig")
        vault=(ROOT/"core"/"krishna_core"/"secure_vault.py").read_text(encoding="utf-8-sig")
        self.assertIn('if path == "/health":',server)
        self.assertIn('if path == "/api/status":',server)
        health_block=server.split('if path == "/health":',1)[1].split('if path == "/api/status":',1)[0]
        self.assertNotIn("watcher.snapshot()",health_block)
        self.assertNotIn("orch.agi_status()",health_block)
        for token in ("shutdown_runtime_services()", "_autonomy.stop", "_narad_scheduler.stop",
                      "_worker_resilience.stop", "pc_observer.stop", "watcher.stop",
                      "_voice.wake.stop", "_garudanetra.close_all"):
            self.assertIn(token,server)
        for source in (executor,workers):
            self.assertIn("split_command(",source)
            self.assertIn("shell=False",source)
            self.assertNotIn('shlex.split(command,posix=os.name!="nt")',source)
        voice=(ROOT/"core"/"krishna_core"/"native_voice.py").read_text(encoding="utf-8-sig")
        self.assertIn("split_command(",voice)
        self.assertNotIn('shlex.split(self.raw,posix=os.name!="nt")',voice)
        self.assertIn("kernel32.LocalFree(ctypes.cast(desc,ctypes.c_void_p))",vault)

    def test_one_canonical_mobile_build_workflow(self):
        workflows=ROOT/".github"/"workflows"
        self.assertTrue((workflows/"build-mobile-v3.yml").is_file())
        self.assertFalse((workflows/"build-apk.yml").exists())
        text=(workflows/"build-mobile-v3.yml").read_text(encoding="utf-8-sig")
        self.assertIn("fix/krishna-ui-runtime-verification",text)
        self.assertIn("stale hard-coded PC IP",text)

    def test_start_script_has_separate_lan_and_private_overlay_modes(self):
        text=(ROOT/"scripts"/"START_KRISHNA.ps1").read_text(encoding="utf-8-sig")
        for token in ("$MobileLan","KRISHNA_LAN_DISCOVERY","0.0.0.0","$PrivateRemote -and $MobileLan"):
            self.assertIn(token,text)

    def test_deploy_copies_and_tracks_avatar_preview_without_private_glb(self):
        text=(ROOT/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('avatar\\krishna_child_360.webp.b64',text)
        self.assertIn('Copy-Item -Force $avatarPreviewSource $avatarPreviewRuntime',text)
        self.assertIn('$Runtime\\avatar\\krishna_child_360.webp.b64',text)
        self.assertIn('dashboard\\assets\\avatar',text)
        self.assertNotIn('Copy-Item -Force "$Source\\dashboard\\assets\\avatar',text)

    def test_avatar_engine_is_local_pinned_and_served_from_runtime(self):
        installer=(ROOT/"scripts"/"INSTALL_AVATAR_ENGINE.ps1").read_text(encoding="utf-8-sig")
        deploy=(ROOT/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8-sig")
        server=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8-sig")
        web=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        self.assertIn("met4citizen/TalkingHead",installer)
        self.assertIn("eed58d198076a7e1e825f804802921c4d3804d46",installer)
        self.assertIn("met4citizen/HeadAudio",installer)
        self.assertIn("d3af5f9ff86ab6b2b1913d411a4e1922ec101953",installer)
        self.assertIn("lhupyn/motion-engine",installer)
        self.assertIn("bd780a19e10d1cc5736a77946b04e08d658d5bf8",installer)
        self.assertIn("@google/model-viewer@$ModelViewerVersion",installer)
        self.assertIn("dashboard\\assets\\avatar-engine",deploy)
        self.assertIn("INSTALL_AVATAR_ENGINE.ps1",deploy)
        self.assertIn("PREPARE_KRISHNA_AVATAR.ps1",deploy)
        self.assertIn('path.startswith("/assets/avatar-engine/")',server)
        self.assertIn('"talkinghead_installed"',server)
        self.assertIn('"headaudio_installed"',server)
        self.assertIn('"motion_engine_installed"',server)
        self.assertIn('"model_viewer_installed"',server)
        self.assertIn("await import('talkinghead')",web)
        self.assertIn("MotionEngine",web)
        self.assertIn("HeadAudio",web)
        self.assertIn('src="/assets/avatar-engine/model-viewer/model-viewer.min.js"',web)
        self.assertNotIn("ajax.googleapis.com/ajax/libs/model-viewer",web)

    def test_private_avatar_production_pipeline_preserves_source_and_fails_closed(self):
        prepare=(ROOT/"scripts"/"PREPARE_KRISHNA_AVATAR.ps1").read_text(encoding="utf-8-sig")
        audit=(ROOT/"core"/"krishna_core"/"avatar_asset_pipeline.py").read_text(encoding="utf-8-sig")
        cli=(ROOT/"scripts"/"avatar_asset_audit.py").read_text(encoding="utf-8-sig")
        server=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8-sig")
        for token in ("krishna.glb","krishna.production.glb","candidates","production-pipeline.json",
                      "cloud_upload_used=$false","Make-It-Animatable","Motius","--method template"):
            self.assertIn(token,prepare)
        self.assertNotIn("--method make-it-animatable",prepare)
        self.assertNotIn("--method mia",prepare)
        self.assertIn("TALKINGHEAD_BONES",audit)
        self.assertIn("MIXAMO_FINGERS",audit)
        self.assertIn("ARKIT_52",audit)
        self.assertIn("OCULUS_15",audit)
        self.assertIn("source GLB is never modified",audit)
        self.assertIn("inspect_avatar",cli)
        self.assertIn('if path == "/api/avatar/asset-audit":',server)
        self.assertIn("AVATAR_PRODUCTION_GLB",server)
        self.assertIn('promotion_policy',server)

    def test_live_ui_inspection_does_not_require_network_idle(self):
        text=(ROOT/"core"/"krishna_core"/"browser_operator.py").read_text(encoding="utf-8-sig")
        inspect=text.split("    def inspect(",1)[1]
        self.assertIn('page.goto(url, wait_until="domcontentloaded")',inspect)
        self.assertNotIn('page.goto(url, wait_until="networkidle")',inspect)

    def test_acceptance_report_is_windows_powershell_51_safe(self):
        text=(ROOT/"scripts"/"ACCEPT_KRISHNA_RUNTIME.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('$checkRows=@($checks | ForEach-Object { $_ })',text)
        self.assertIn('checks=$checkRows',text)
        self.assertNotIn('checks=@($checks)',text)
        self.assertIn('[void]$proc.WaitForExit(5000)',text)


    def test_dashboard_has_no_implicit_favicon_404(self):
        web=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        server=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8-sig")
        self.assertIn('<link rel="icon" href="data:,">',web)
        self.assertIn('if path == "/favicon.ico":',server)
        self.assertIn('return self._binary(204, b"", "image/x-icon")',server)

    def test_e_drive_audit_report_is_windows_powershell_51_safe(self):
        text=(ROOT/"scripts"/"AUDIT_KRISHNA_E_DRIVE.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('$findingRows=@($findings | ForEach-Object { $_ })',text)
        self.assertIn('findings=$findingRows',text)
        self.assertNotIn('findings=@($findings)',text)
        self.assertIn('OPENMONTAGE_BRIDGE_READY',text)

    def test_e_drive_cleanup_audit_is_read_only_and_covers_named_roots(self):
        text=(ROOT/"scripts"/"AUDIT_KRISHNA_E_DRIVE.ps1").read_text(encoding="utf-8-sig")
        for token in (
            'E:\\KRISHNA',
            'E:\\KRISHNA-SOURCE',
            'E:\\Krishna-The',
            'E:\\Krishna-The GOD',
            'E:\\KRISHNA-CBM',
            'E:\\KRISHNA-E2E-PROBE',
            'E:\\KRISHNA-AUDIT',
            'E:\\New folder',
            '8765','8766','8876','11434',
            'CANONICAL SOURCE','ACTIVE RUNTIME','REQUIRED DATA','BACKUP','CACHE',
            'TEST/PROBE','OLD/STAGING','DUPLICATE','UNKNOWN - DO NOT DELETE',
            'PRE-CANONICAL-SYNC-20260923-213620',
            'automatic_delete_allowed=$false',
            'deletion_performed=$false',
        ):
            self.assertIn(token,text)
        for destructive in ('Remove-Item','Stop-Process','taskkill.exe','rd /s','rmdir /s'):
            self.assertNotIn(destructive,text)

    def test_e_drive_audit_handles_live_locked_files_without_false_missing(self):
        text=(ROOT/"scripts"/"AUDIT_KRISHNA_E_DRIVE.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("Get-HashProbe",text)
        self.assertIn("Get-FileHash -Algorithm SHA256 -LiteralPath $Path -ErrorAction Stop",text)
        self.assertIn('"locked_or_in_use"',text)
        self.assertIn("candidate_exists=$a.exists",text)
        self.assertIn("canonical_exists=$b.exists",text)
        self.assertIn("=== KRISHNA PROCESS OWNERSHIP ===",text)
        self.assertIn("=== KRISHNA LISTENERS ===",text)

    def test_start_output_uses_ascii_separators(self):
        text=(ROOT/"scripts"/"START_KRISHNA.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('| discovery ON | pairing required',text)
        self.assertIn('| PRIVATE OVERLAY | pairing required',text)
        self.assertNotIn(' · ',text)

    def test_sidebar_is_minimal_with_expandable_projects_and_separate_chats(self):
        web=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        aside=web.split('<aside class="side">',1)[1].split('</aside>',1)[0]
        self.assertIn('<div class="section">MAIN MENU</div>',aside)
        self.assertIn("<span class=\"txt\">KRISHNA</span>",aside)
        self.assertIn("<span class=\"txt\">Sudarshan</span>",aside)
        self.assertIn("<span class=\"txt\">Plugins</span>",aside)
        for hidden_runtime in ("KABACH","Garuda","Garudanetra","BRAHMAGYAN","Gyan-Bhandar","NARAD","Specialists","Developer","UI Guardian","Work progress","Activity","System","TOOLS"):
            self.assertNotIn(hidden_runtime,aside)
        self.assertIn('<span>PROJECTS</span>',aside)
        self.assertIn('id="projectMenuTree"',aside)
        self.assertIn('<span>CHATS</span>',aside)
        self.assertIn('title="Create project"',aside)
        self.assertIn('onclick="openNewProjectWizard()"',aside)
        self.assertIn('title="Add new chat"',aside)
        self.assertIn('id="recentChats"',aside)
        self.assertNotIn('Project Chats',aside)
        self.assertIn('function loadGeneralChats()',web)
        self.assertIn("ch.project==='KRISHNA'||ch.project==='general'",web)
        self.assertIn('function selectSidebarProject(name)',web)
        self.assertIn("className='projectBranch'+(expanded?' expanded':'')",web)
        self.assertIn("className='projectNestedChats'",web)
        self.assertIn("openProjectActionMenu",web)
        self.assertIn("data-project-action=\"rename\"",web)
        self.assertIn("data-project-action=\"share\"",web)
        self.assertIn("data-project-action=\"delete\"",web)

    def test_garuda_and_garudanetra_are_distinct_internal_runtime_roles(self):
        web=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        garuda=(ROOT/"core"/"krishna_core"/"garuda.py").read_text(encoding="utf-8-sig")
        aside=web.split('<aside class="side">',1)[1].split('</aside>',1)[0]
        self.assertNotIn("<span class=\"txt\">Garuda</span>",aside)
        self.assertNotIn("<span class=\"txt\">Garudanetra</span>",aside)
        self.assertIn('<section id="garuda" class="view panelView">',web)
        self.assertIn('<section id="garudanetra" class="view panelView">',web)
        self.assertIn('id="garudaGoal"',web)
        self.assertIn('id="garudanetraGoal"',web)
        self.assertIn('onclick="runGaruda()"',web)
        self.assertIn('onclick="startGarudanetraMission()"',web)
        self.assertNotIn("document.querySelector('#garuda button')",web)
        self.assertIn('"agent":"Garuda"',garuda)
        self.assertIn('Garuda requires a research goal',garuda)

    def test_garudanetra_ui_uses_browser_fabric_not_garuda_research(self):
        web=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        section=web.split('<section id="garudanetra"',1)[1].split('<section id="narad"',1)[0]
        self.assertIn('id="garudanetraEngine"',section)
        self.assertIn('id="garudanetraStream"',section)
        self.assertIn('id="garudanetraRefs"',section)
        self.assertIn('id="garudanetraRecording"',section)
        mission=web.split("async function startGarudanetraMission()",1)[1].split("function naradTriggerChanged",1)[0]
        self.assertNotIn("/api/garuda/scout",mission)
        self.assertIn("Garuda owns research; Garudanetra owns browser execution",mission)
        self.assertIn("/api/garudanetra/fabric",web)

    def test_priority_operational_ui_has_no_legacy_mutation_bypass(self):
        web=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        for path in (
            "/api/garuda/scout","/api/garudanetra/session/start","/api/garudanetra/session/control",
            "/api/chats/create","/api/chats/move","/api/chats/rename","/api/chats/delete",
            "/api/projects/register",
        ):
            self.assertNotIn(path,web)
        for action in (
            "project.register","chat.create","chat.move","chat.rename","chat.delete",
            "garuda.scout","garudanetra.start","garudanetra.control","garudanetra.upload_attachment",
        ):
            self.assertEqual(web.count("actionReq('"+action+"'"),1,action)

    def test_mobile_action_sync_stays_conversation_status_only(self):
        mobile=(ROOT/"mobile_v3"/"index.html").read_text(encoding="utf-8-sig")
        self.assertIn("e.type==='action.sync'",mobile)
        self.assertIn("setMode('WORKING',action)",mobile)
        for forbidden in ("filesystem.write","system.run","credentials.read","trade.execute"):
            self.assertNotIn(forbidden,mobile)

    def test_brahmagyan_dashboard_is_compact_and_not_an_always_on_agent_fleet(self):
        web=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        bg=(ROOT/"core"/"krishna_core"/"brahmagyan.py").read_text(encoding="utf-8-sig")
        council=(ROOT/"core"/"krishna_core"/"rishi_council.py").read_text(encoding="utf-8-sig")
        aside=web.split('<aside class="side">',1)[1].split('</aside>',1)[0]
        self.assertNotIn("<span class=\"txt\">BRAHMAGYAN</span>",aside)
        self.assertIn('<section id="brahmagyan" class="view panelView">',web)
        self.assertIn('id="brahmaCouncil"',web)
        self.assertIn('id="brahmaMissions"',web)
        self.assertIn('id="brahmaCuriosity"',web)
        self.assertIn("no autonomous background daemon",bg)
        self.assertIn('"running_processes":0',council)
        self.assertNotIn("while True",bg)
        self.assertNotIn("ThreadPoolExecutor",bg)

    def test_avatar_runtime_uses_character_bible_not_two_state_stub(self):
        server=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8-sig")
        web=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        avatar=(ROOT/"core"/"krishna_core"/"avatar_fabric.py").read_text(encoding="utf-8-sig")
        self.assertIn('orch.agi.avatar.state_for_activity',server)
        self.assertNotIn('"avatar_state": "FLUTE" if current == "Idle" else "WORKING"',server)
        self.assertIn("avatarState(d.avatar_state",web)
        self.assertIn("PERFORMANCE_CHANNELS",avatar)
        self.assertIn("SURFACE_CONTRACT",avatar)

    def test_narad_n8n_dashboard_is_observability_not_embedded_editor(self):
        web=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        self.assertIn('id="naradLoad"',web)
        self.assertIn('id="naradConnectorCount"',web)
        self.assertIn('id="naradN8n"',web)
        self.assertIn("req('/api/narad/connectors')",web)
        self.assertNotIn('iframe src="http://localhost:5678',web)
        self.assertNotIn('iframe src="https://',web.split('<section id="narad"',1)[1].split('</section>',1)[0])

if __name__=="__main__":
    unittest.main()
