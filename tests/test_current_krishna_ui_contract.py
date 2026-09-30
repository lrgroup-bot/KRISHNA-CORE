import re
import unittest
from pathlib import Path


class CurrentKrishnaUIContractTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).resolve().parents[1]
        self.html=(self.root/"core"/"web_validation.html").read_text(encoding="utf-8")
        self.accept=(self.root/"scripts"/"ACCEPT_KRISHNA_RUNTIME.ps1").read_text(encoding="utf-8")
        self.orchestrator=(self.root/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")

    def test_current_ui_has_explicit_version_marker(self):
        self.assertIn('name="krishna-ui-version" content="2026.09-current"',self.html)
        self.assertIn('data-krishna-ui="2026.09-current"',self.html)

    def test_main_menu_contains_only_krishna_and_sudarshan(self):
        m=re.search(r'(?s)<div class="section">MAIN MENU</div><div class="nav mainMenuNav">(.*?)</div>\s*<div class="sidebarWorkspace">',self.html)
        self.assertIsNotNone(m)
        menu=m.group(1)
        self.assertEqual(menu.count("<button"),2)
        self.assertIn("showView('home')",menu)
        self.assertIn("showView('sudarshan')",menu)
        for hidden in ("manibhadra","vanijya","workingGods","kabach","garuda","garudanetra","brahmagyan","gyan","narad","specialists","developer","work","activity","system"):
            self.assertNotIn(f"showView('{hidden}')",menu)

    def test_plugins_live_at_sidebar_bottom(self):
        self.assertRegex(self.html,r'<div class="nav bottomNav"[^>]*>\s*<button[^>]+showView\(\'plugins\'\)')
        main=re.search(r'(?s)<div class="section">MAIN MENU</div><div class="nav mainMenuNav">(.*?)</div>\s*<div class="sidebarWorkspace">',self.html).group(1)
        self.assertNotIn("showView('plugins')",main)

    def test_lr_group_commerce_is_absent_from_krishna(self):
        for token in ("MANIBHADRA","VĀṆIJYA","VANIJYA","manibhadra.","vanijya.","vanik_netra."):
            self.assertNotIn(token,self.html)
            self.assertNotIn(token,self.orchestrator)
        for name in (
            "manibhadra_advisor.py","manibhadra_commerce.py","manibhadra_crm.py",
            "vanijya_sales.py","vanik_netra.py","vanik_netra_sources.py","vanik_netra_store.py",
            "commerce_expansion.py","commerce_expansion_adapters.py","marketplace_adapters.py","affiliate_intent.py",
        ):
            self.assertFalse((self.root/"core"/"krishna_core"/name).exists(),name)

    def test_system_orbit_has_live_status_and_click_details(self):
        for token in (
            'id="opsInformer"','id="workingGodsMini"','id="godDetailDialog"',
            'class="systemOrbitHead"',"function openGodDetail(id)","row.dataset.label",
        ):
            self.assertIn(token,self.html)
        qc=(self.root/"core"/"krishna_core"/"brahma_process_qc.py").read_text(encoding="utf-8")
        for token in ("Suryadev","Chandradev","Mrityunjaya","UI Guardian","Developer","Specialists","Project Perfection"):
            self.assertIn(token,qc)

    def test_sudarshan_is_clean_conversation_workspace(self):
        self.assertIn("SUDARSHAN CLEAN CHAT MODE",self.html)
        self.assertRegex(self.html,r'#sudarshan \.sudarshanBar\{\s*display:none !important;')
        self.assertRegex(self.html,r'#sudarshan \.holoRail\{\s*display:none !important;')

    def test_legacy_dashboard_is_absent_and_deploy_purges_runtime_copy(self):
        self.assertFalse((self.root/"core"/"dashboard.html").exists())
        deploy=(self.root/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        self.assertIn('$legacyDashboard=Join-Path $Runtime "core\\dashboard.html"',deploy)
        self.assertIn('Remove-Item -Force $legacyDashboard',deploy)

    def test_manual_windows_build_uses_canonical_desktop_shell(self):
        build=(self.root/"BUILD_KRISHNA_AGI.ps1").read_text(encoding="utf-8")
        self.assertIn("krishna_desktop.py",build)
        self.assertIn("web_validation.html",build)
        self.assertIn("--collect-all webview",build)
        self.assertNotIn("core\\run_core.py",build)

    def test_start_reconciles_runtime_drift_through_verified_deploy(self):
        start=(self.root/"scripts"/"START_KRISHNA.ps1").read_text(encoding="utf-8")
        self.assertIn("Re-running verified deployment",start)
        self.assertIn("Automatic drift reconciliation deployment failed",start)

    def test_runtime_acceptance_rejects_old_ui(self):
        for token in (
            'Current KRISHNA UI','2026.09-current','Old or mismatched KRISHNA desktop design detected',
            'SUDARSHAN CLEAN CHAT MODE','$mainMenuButtonCount -eq 2',
        ):
            self.assertIn(token,self.accept)


if __name__=="__main__":
    unittest.main()
