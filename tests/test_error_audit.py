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

    def test_start_output_uses_ascii_separators(self):
        text=(ROOT/"scripts"/"START_KRISHNA.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('| discovery ON | pairing required',text)
        self.assertIn('| PRIVATE OVERLAY | pairing required',text)
        self.assertNotIn(' · ',text)

    def test_sidebar_has_project_names_and_separate_gpt_style_chats(self):
        web=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        aside=web.split('<aside class="side">',1)[1].split('</aside>',1)[0]
        self.assertIn('id="projectMenuToggle"',aside)
        self.assertIn('<span class="txt">Project</span>',aside)
        self.assertIn('id="projectMenuTree"',aside)
        self.assertIn('id="chatMenuToggle"',aside)
        self.assertIn('<span class="txt">Chats</span>',aside)
        self.assertIn('id="recentChats"',aside)
        self.assertNotIn('Project Chats',aside)
        self.assertIn('function loadGeneralChats()',web)
        self.assertIn("ch.project==='KRISHNA'||ch.project==='general'",web)
        self.assertIn('function selectSidebarProject(name)',web)

    def test_garuda_and_garudanetra_are_distinct_ui_and_runtime_roles(self):
        web=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        garuda=(ROOT/"core"/"krishna_core"/"garuda.py").read_text(encoding="utf-8-sig")
        aside=web.split('<aside class="side">',1)[1].split('</aside>',1)[0]
        self.assertIn("showView('garuda')",aside)
        self.assertIn('<span class="txt">Garuda</span>',aside)
        self.assertIn("showView('garudanetra')",aside)
        self.assertIn('<span class="txt">Garudanetra</span>',aside)
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
