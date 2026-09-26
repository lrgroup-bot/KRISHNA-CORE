import unittest
from pathlib import Path


class VanikNetraUIContractTests(unittest.TestCase):
    def test_manibhadra_market_scanner_surface_exists(self):
        root=Path(__file__).resolve().parents[2]
        html=(root/"core"/"web_validation.html").read_text(encoding="utf-8")
        for token in (
            "VANIK-NETRA · Market Scanner",
            "id=\"maniMarketArea\"",
            "function vanikNetraScan()",
            "function vanikNetraChanges()",
            "vanik_netra.scan",
            "vanik_netra.crm.import",
            "No outreach sent.",
        ):
            self.assertIn(token,html)

    def test_vanik_netra_is_not_a_main_menu_item(self):
        root=Path(__file__).resolve().parents[2]
        html=(root/"core"/"web_validation.html").read_text(encoding="utf-8")
        menu=html.split('<div class="section">MAIN MENU</div>',1)[1].split('<div class="sidebarWorkspace">',1)[0]
        self.assertNotIn("VANIK-NETRA",menu)


if __name__=="__main__":
    unittest.main()
