from pathlib import Path
import unittest


CORE = Path(__file__).resolve().parents[1]
HTML = (CORE / "web_validation.html").read_text(encoding="utf-8")
SERVER = (CORE / "krishna_core" / "server.py").read_text(encoding="utf-8")
QC = (CORE / "krishna_core" / "brahma_process_qc.py").read_text(encoding="utf-8")


class OwnerSystemDashboardContractTests(unittest.TestCase):
    def test_universal_operational_dashboard_exists(self):
        self.assertIn('id="systemDashboard"', HTML)
        for field in (
            "systemDashCurrent", "systemDashResult", "systemDashProblems",
            "systemDashOwner", "systemDashHistory", "systemDashRaw",
        ):
            self.assertIn(f'id="{field}"', HTML)

    def test_system_rail_shows_names_on_desktop(self):
        self.assertIn('id="krishna-owner-system-dashboard-v1"', HTML)
        self.assertIn(".miniGodName{\n position:static!important", HTML)
        self.assertIn("grid-template-columns:32px minmax(0,1fr)", HTML)

    def test_owner_status_language_is_not_red_for_idle(self):
        self.assertIn("return {label:'IDLE · READY',color:'yellow'}", HTML)
        self.assertIn("return {label:'HEALING',color:'blue'}", HTML)
        self.assertIn("return {label:'WAITING FOR PARTHA',color:'amber'}", HTML)
        self.assertIn("return {label:'BLOCKED',color:'red'}", HTML)

    def test_backend_status_colors_match_owner_language(self):
        self.assertIn('return "green"', QC)
        self.assertIn('return "blue"', QC)
        self.assertIn('return "amber"', QC)
        self.assertIn('return "red"', QC)
        self.assertIn('return "yellow"', QC)
        self.assertNotIn('god["color"]="green" if god["active"] else "red"', QC)

    def test_sudarshan_composer_does_not_expose_manual_research_modes(self):
        marker = 'class="composerWrap"'
        start = HTML.index(marker)
        end = HTML.index("</main>", start)
        composer = HTML[start:end]
        self.assertIn("＋ File", composer)
        self.assertIn("＋ Plugin", composer)
        self.assertIn("◇ Project", composer)
        self.assertNotIn("⌕ Investigate", composer)
        self.assertNotIn("⌁ Research", composer)

    def test_key_systems_have_live_backend_sources(self):
        required = {
            "amcc": "/api/amcc/status",
            "chandradev": "/api/chandradev/status",
            "hawkeye": "/api/hawkeye/status",
            "suryadev": "/api/suryadev/status",
            "mrityunjaya": "/api/mrityunjay/status",
            "brahma": "/api/brahma/status",
            "sudarshan": "/api/sudarshan/runtime",
            "perfection": "/api/project-perfection/status",
        }
        for system_id, endpoint in required.items():
            self.assertIn(f"{system_id}:'{endpoint}", HTML)
            self.assertIn(f'path == "{endpoint}"', SERVER)


if __name__ == "__main__":
    unittest.main()
