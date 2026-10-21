"""UI regression checks: date controls and live connection LEDs."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
class DashboardVisibleTests(unittest.TestCase):
    def test_visible_controls(self):
        html = (ROOT/"dashboard.html").read_text(encoding="utf-8")
        for element in ("date-main", "date-today-main", "date-previous-main",
                        "date-next-main", "date-clear-main", "date-center",
                        "krishna-led", "brahmagyan-led", "rishi-led",
                        "sidebar-bottom", "date-selected-count"):
            with self.subTest(element=element):
                self.assertIn(element, html)
        self.assertIn('href="#date-center"', html)
        self.assertIn("UI v6", html)

    def test_controls_have_js_handlers(self):
        js = (ROOT/"dashboard.js").read_text(encoding="utf-8")
        for element in ("date-main", "date-today-main", "date-previous-main",
                        "date-next-main", "date-clear-main"):
            with self.subTest(element=element):
                self.assertIn('"'+element+'").addEventListener', js)
        self.assertIn('date: app.selectedDay', js)
        self.assertIn('fetch("/api/diary?date="', js)

    def test_status_panel_stays_visible_at_mobile_width(self):
        css = (ROOT/"dashboard.css").read_text(encoding="utf-8")
        self.assertIn(".sidebar-bottom .status-leds", css)
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))", css)
        self.assertIn(".date-center", css)

if __name__ == "__main__":
    unittest.main()
