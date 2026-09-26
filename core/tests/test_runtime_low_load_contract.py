import unittest
from pathlib import Path


class RuntimeLowLoadContractTests(unittest.TestCase):
    def test_server_uses_bounded_background_observer_defaults(self):
        root=Path(__file__).resolve().parents[2]
        server=(root/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8")
        self.assertIn('KRISHNA_PC_OBSERVER_INTERVAL_SECONDS","30"',server)
        self.assertIn('KRISHNA_PC_OBSERVER_MAX_FILES_PER_PROJECT","2500"',server)
        self.assertIn('KRISHNA_SCIENCE_RESEARCH_INTERVAL_SECONDS","1800"',server)
        self.assertIn('KRISHNA_BRAHMA_CONSOLIDATION_INTERVAL_SECONDS","1800"',server)

    def test_optional_capabilities_do_not_start_daemons(self):
        root=Path(__file__).resolve().parents[2]
        optional=(root/"core"/"krishna_core"/"optional_capabilities.py").read_text(encoding="utf-8")
        fabric=(root/"core"/"krishna_core"/"capability_fabric.py").read_text(encoding="utf-8")
        self.assertNotIn("threading.Thread",optional)
        self.assertIn('"always_on_heavy_runtime":False',fabric)
        self.assertIn('"automatic_download":False',optional)


if __name__=="__main__":
    unittest.main()
