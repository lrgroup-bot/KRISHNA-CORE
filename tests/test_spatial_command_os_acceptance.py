import re
import unittest
from pathlib import Path


class SpatialCommandOSAcceptanceTests(unittest.TestCase):
    """Seeded acceptance checks for the 2026-10-05 KRISHNA UI/authority handover.

    These tests are intentionally strict: they turn the audited UI/authority gaps into
    executable contracts before source changes are promoted or deployed.
    """

    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.html = (self.root / "core" / "web_validation.html").read_text(encoding="utf-8")
        self.spatial_app = (self.root / "app" / "spatial-ui" / "src" / "App.tsx").read_text(encoding="utf-8")

    def test_live_system_rail_keeps_owner_visible_names(self):
        """Upper system controls must not become icon-only by visually clipping names."""
        hidden_name_rule = re.compile(
            r"\.miniGodName\s*,\s*\.miniGodState\s*\{[^}]*"
            r"(?:width\s*:\s*1px|clip\s*:\s*rect\(|display\s*:\s*none)",
            re.IGNORECASE | re.DOTALL,
        )
        self.assertIsNone(
            hidden_name_rule.search(self.html),
            "System rail names/states are visually hidden; owner-facing labels must remain readable.",
        )

    def test_idle_ready_is_not_rendered_as_error_red(self):
        """Healthy idle/ready systems must not share BLOCKED/ERROR red semantics."""
        self.assertNotIn(
            ".godLight.status-yellow{background:#cb4f5a",
            self.html,
            "status-yellow is currently mapped to red; IDLE/READY needs a non-error color.",
        )
        self.assertNotRegex(
            self.html,
            r"Red\s*=\s*idle\s+or\s+not\s+active",
            "Owner copy still defines healthy idle as red/error-like.",
        )

    def test_owner_status_grammar_declares_required_states(self):
        """Canonical UI should expose the agreed owner-facing status vocabulary."""
        normalized = self.html.upper()
        required = (
            "WORKING",
            "IDLE/READY",
            "HEALING/RECOVERING",
            "WAITING FOR PARTHA",
            "BLOCKED/ERROR",
        )
        for state in required:
            self.assertIn(state, normalized, f"Missing canonical owner status state: {state}")

    def test_normal_sudarshan_composer_has_no_manual_research_mode_buttons(self):
        """KRISHNA chooses Investigate/Research internally; normal composer must stay simple."""
        composer_start = self.html.find('<div class="composerWrap">')
        script_start = self.html.find("<script>", composer_start)
        self.assertGreaterEqual(composer_start, 0, "Composer not found")
        self.assertGreater(script_start, composer_start, "Composer boundary not found")
        composer = self.html[composer_start:script_start]
        self.assertNotRegex(composer, r"onclick=\"investigate\(\)\"", "Manual Investigate control remains in normal composer")
        self.assertNotRegex(composer, r"onclick=\"research\(\)\"", "Manual Research control remains in normal composer")

    def test_frontend_cannot_self_assert_approval(self):
        """Caller-supplied approved=true must never be treated as executable authority."""
        self.assertIsNone(
            re.search(r"\bapproved\s*:\s*true\b", self.spatial_app),
            "Frontend still self-asserts approved:true; use a Sudarshan-minted authority contract instead.",
        )

    def test_operational_metrics_default_to_unknown_not_invented(self):
        """Unknown backend data must be rendered honestly rather than fabricated."""
        forbidden_examples = (
            '>99<',
            '>100%<',
            'data-fake-metric=',
        )
        for token in forbidden_examples:
            self.assertNotIn(token, self.html)


if __name__ == "__main__":
    unittest.main()
