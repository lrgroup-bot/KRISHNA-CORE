import os
import unittest
from pathlib import Path


def repository_root():
    env=os.getenv("KRISHNA_SOURCE_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


class GarudanetraBrowserWorkspaceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(repository_root()/"core"/"web_validation.html").read_text(encoding="utf-8")

    def test_indexeddb_workspace_is_browser_local_and_sanitized(self):
        self.assertIn("krishna-garudanetra-workspace-v1",self.html)
        self.assertIn("indexedDB.open",self.html)
        self.assertIn("garudanetraSanitizeText",self.html)
        self.assertIn("GARUDA_SENSITIVE_KEY",self.html)
        self.assertIn("CLEAR LOCAL CACHE",self.html)
        self.assertIn("Authoritative KRISHNA evidence will not be deleted",self.html)

    def test_research_fabric_ui_exposes_missions_scouts_and_handoffs(self):
        for action in (
            "garudanetra.research.create",
            "garudanetra.research.launch",
            "garudanetra.research.analyze",
            "garudanetra.research.handoff",
        ):
            self.assertIn(action,self.html)
        self.assertIn("CREATE RESEARCH MISSION",self.html)
        self.assertIn("SHOW SKILLS",self.html)
        self.assertIn("→ RISHI",self.html)
        self.assertIn("→ LAB BOT",self.html)

    def test_ui_does_not_rebrand_jetbot_as_browser_authority(self):
        self.assertIn("RESEARCH FABRIC v2 · JETBOT-INSPIRED",self.html)
        self.assertIn("Playwright remains the browser authority",self.html)


if __name__=="__main__":
    unittest.main()
