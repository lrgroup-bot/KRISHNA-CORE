import unittest
from pathlib import Path

class WebValidationTests(unittest.TestCase):
    def test_validation_ui_contains_real_core_workflows(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "web_validation.html").read_text(encoding="utf-8")
        for endpoint in (
            "/api/status", "/api/projects", "/api/core/chat",
            "/api/projects/index", "/api/investigate",
            "/api/browser/inspect", "/api/research/github", "/api/plugins", "/api/tasks",
        ):
            self.assertIn(endpoint, text)
        self.assertIn("Run API checks", text)
        # KRISHNA is the sole public identity. Internal work engines are
        # intentionally selected by Core rather than exposed as manual modes.
        self.assertIn("Command KRISHNA through Sudarshan", text)
        self.assertIn("Conversation", text)
        self.assertIn("Work progress", text)
        self.assertNotIn("Karma · Work", text)
        self.assertNotIn("Vishwakarma · Code", text)

    def test_command_center_v4_contract(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "web_validation.html").read_text(encoding="utf-8")
        for token in (
            "ACTIVE WORK", "VERIFICATION", "SYSTEM LOAD",
            "GARUDANETRA · PRIVATE", "TAKE CONTROL", "CONTINUE",
            "opsInformer", "liveWork", "refreshCommandCenter",
            "startGarudanetraMission", "/api/garuda/scout", "loadGarudanetra",
            "/api/garudanetra/session/start", "/api/garudanetra/session/control", "/api/garudanetra/frame",
            "garudaFrame", "garudaOwnerControl", "owner_control", "startGarudanetraPolling",
            "/api/narad/status", "/api/narad/workflows", "/api/narad/history",
            "/api/narad/connections", "/api/narad/dead-letters", "/api/narad/scheduler",
            "/api/narad/connections/register", "/api/narad/webhooks/provision", "/api/narad/dead-letters/retry",
            "naradTriggerType", "naradConnectionCount", "naradDeadLetters", "registerNaradConnection", "provisionNaradWebhook",
            "/api/kabach/projects", "/api/runtime/integrity", "KABACH", "deployIntegrity",
            "/api/commitments", "/api/commitments/update", "/api/autonomy/status", "/api/autonomy/tick", "commitmentSummary", "autonomySummary", "runAutonomyTick", "Auto Inspect", "/api/models", "modelRouter",
            "/api/runtime/audit", "driveAudit",
            "/api/requirements", "requirementsCount", "loadRequirementsLedger",
            "/api/ui-guardian/registry", "/api/ui-guardian/evaluate", "/api/ui-guardian/transition",
            "UI Guardian", "Evaluate 4 viewports", "promoteUIGuardian",
            "gyanInventory", "gyanKind", "loadGyanInventory", "supersedeGyan",
            "/api/ui-guardian/registry", "/api/ui-guardian/evaluate", "/api/ui-guardian/transition",
            "uiGuardianRegistry", "Run viewport matrix", "Stable / Candidate / Experimental / Rejected",
        ):
            self.assertIn(token, text)
        self.assertIn("Garudanetra", text)
        self.assertNotIn("Garuda never implements directly", text)
        # High-visibility legacy mojibake must not regress.
        for broken in ("â€¢â€¢â€¢", "ðŸ¦…", "âŒ¬", "âœ¦", "ï¼‹"):
            self.assertNotIn(broken, text)

    def test_server_exposes_validation_route(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "krishna_core" / "server.py").read_text(encoding="utf-8")
        self.assertIn('"/web-test"', text)
        self.assertIn("WEB_VALIDATION", text)

if __name__ == "__main__":
    unittest.main()
