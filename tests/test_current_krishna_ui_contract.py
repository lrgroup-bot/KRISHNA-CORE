import re
import unittest
from pathlib import Path


class CurrentKrishnaUIContractTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).resolve().parents[1]
        self.html=(self.root/"core"/"web_validation.html").read_text(encoding="utf-8")
        self.accept=(self.root/"scripts"/"ACCEPT_KRISHNA_RUNTIME.ps1").read_text(encoding="utf-8")

    def test_current_ui_has_explicit_version_marker(self):
        self.assertIn('name="krishna-ui-version" content="2026.09-current"',self.html)
        self.assertIn('data-krishna-ui="2026.09-current"',self.html)

    def test_main_menu_contains_only_owner_visible_entries(self):
        m=re.search(r'(?s)<div class="section">MAIN MENU</div><div class="nav mainMenuNav">(.*?)</div>\s*<div class="sidebarWorkspace">',self.html)
        self.assertIsNotNone(m)
        menu=m.group(1)
        self.assertIn("showView('home')",menu)
        self.assertIn("showView('sudarshan')",menu)
        self.assertIn("showView('plugins')",menu)
        for hidden in ("kabach","garuda","garudanetra","brahmagyan","gyan","narad","specialists","developer","work","activity","system"):
            self.assertNotIn(f"showView('{hidden}')",menu)

    def test_sudarshan_is_clean_conversation_workspace(self):
        self.assertIn("SUDARSHAN CLEAN CHAT MODE",self.html)
        self.assertRegex(self.html,r'#sudarshan \.sudarshanBar\{\s*display:none !important;')
        self.assertRegex(self.html,r'#sudarshan \.holoRail\{\s*display:none !important;')

    def test_runtime_acceptance_rejects_old_ui(self):
        for token in (
            'Current KRISHNA UI',
            '2026.09-current',
            'Old or mismatched KRISHNA desktop design detected',
            'SUDARSHAN CLEAN CHAT MODE',
        ):
            self.assertIn(token,self.accept)


if __name__=="__main__":
    unittest.main()
