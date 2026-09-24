from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class KrishnaParthaGitaRepositoryContractTests(unittest.TestCase):
    def test_source_tree_registers_canonical_gita_runtime_files(self):
        tree = (ROOT / "KRISHNA_SOURCE_TREE.txt").read_text(encoding="utf-8-sig")
        for path in (
            r"core\krishna_core\data\bhagavad_gita_700.json",
            r"core\krishna_core\gita_gyan.py",
            r"core\krishna_core\gita_performance.py",
            r"core\krishna_core\krishna_shloka.py",
            r"core\tests\test_gita_performance_conversation.py",
        ):
            self.assertIn(path, tree)

    def test_mobile_stays_conversation_first_with_minimal_gita_controls(self):
        html = (ROOT / "mobile_v3" / "index.html").read_text(encoding="utf-8-sig")
        self.assertIn('id="gitaCard"', html)
        self.assertIn('id="gitaSanskrit"', html)
        self.assertIn("toggleGitaRecitation()", html)
        self.assertIn("repeatGita()", html)
        self.assertIn("gitaNavigate('previous')", html)
        self.assertIn("gitaNavigate('next')", html)
        self.assertIn("ପୁଣି କୁହ", html)
        self.assertIn("ପଛକୁ", html)
        self.assertIn("ଆଗକୁ", html)
        self.assertIn("speakGitaExplanation()", html)
        self.assertIn("Conversation only", html)
        self.assertNotIn("Gita Dashboard", html)

    def test_mobile_does_not_call_generated_explanation_a_trusted_translation(self):
        html = (ROOT / "mobile_v3" / "index.html").read_text(encoding="utf-8-sig")
        self.assertIn("Trusted translation is not bundled for this verse", html)
        self.assertIn("generated_explanation", html)

    def test_mobile_bridge_can_request_private_gita_audio(self):
        java=(ROOT/"mobile_v3"/"MainActivity.java").read_text(encoding="utf-8-sig")
        self.assertIn("public String gitaSpeak(",java)
        self.assertIn("public String voiceAudioDataUrl(",java)
        self.assertIn('call("/api/gita/speak"',java)
        self.assertIn('"/api/voice/audio?id="',java)

    def test_desktop_popup_is_odia_first_with_gita_navigation(self):
        html=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8-sig")
        self.assertIn('value="or-IN" selected',html)
        self.assertIn("କୁହ ପାର୍ଥ, କଣ ସହାୟତା ଦରକାର?",html)
        self.assertIn("krishnaGitaControl('previous')",html)
        self.assertIn("krishnaGitaControl('repeat')",html)
        self.assertIn("krishnaGitaControl('next')",html)
        self.assertIn("speakKrishnaGita",html)

    def test_server_routes_partha_gita_followups(self):
        server = (ROOT / "core" / "krishna_core" / "server.py").read_text(encoding="utf-8-sig")
        self.assertIn("gita_followup_markers", server)
        self.assertIn("gita_situation_markers", server)
        self.assertIn("orch.gita_shloka.last_reference()", server)


if __name__ == "__main__":
    unittest.main()
