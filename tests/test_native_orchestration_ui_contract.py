import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class NativeOrchestrationUIContractTests(unittest.TestCase):
    def setUp(self):
        self.ui=(ROOT/"core"/"orchestration_control.html").read_text(encoding="utf-8")
        self.server=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8")
        self.main=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8")

    def test_orchestration_surface_is_native_and_read_only(self):
        self.assertIn('data-krishna-orchestration-ui="2026.10-native"',self.ui)
        for endpoint in (
            "/api/missions?limit=40","/api/queue/status","/api/queue?limit=30",
            "/api/events?limit=50","/api/narad/dead-letters","/api/narad/checkpoints",
        ):
            self.assertIn(endpoint,self.ui)
        self.assertNotIn("method:'POST'",self.ui)
        self.assertNotIn('method:"POST"',self.ui)

    def test_server_serves_orchestration_without_second_runtime(self):
        self.assertIn('ORCHESTRATION_CONTROL',self.server)
        self.assertIn('path == "/orchestration"',self.server)
        self.assertNotIn("LangGraph",self.ui)
        self.assertNotIn("n8n",self.ui)
        self.assertNotIn("COLI",self.ui)

    def test_main_menu_contract_is_preserved(self):
        marker='<div class="section">MAIN MENU</div><div class="nav mainMenuNav">'
        start=self.main.index(marker)+len(marker)
        end=self.main.index('</div>',start)
        menu=self.main[start:end]
        self.assertEqual(menu.count("<button"),2)
        self.assertIn("showView('home')",menu)
        self.assertIn("showView('sudarshan')",menu)
        self.assertIn("location.href='/orchestration'",self.main)

if __name__=="__main__":
    unittest.main()
