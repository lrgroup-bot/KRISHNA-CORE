import json
import os
import unittest
from pathlib import Path


class KrishnaServerPortConstantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.manifest_path = cls.root / "core" / "krishna_core" / "server_ports.json"
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))

    def test_canonical_live_ports(self):
        self.assertEqual(self.manifest["krishna_core"], 8766)
        self.assertEqual(self.manifest["mobile_companion"], 8765)
        self.assertEqual(self.manifest["lan_discovery"], 8767)
        self.assertEqual(len({
            self.manifest["krishna_core"],
            self.manifest["mobile_companion"],
            self.manifest["lan_discovery"],
        }), 3)

    def test_python_runtime_uses_manifest_default(self):
        config = (self.root / "core" / "krishna_core" / "config.py").read_text(encoding="utf-8")
        self.assertIn('with_name("server_ports.json")', config)
        self.assertIn('KRISHNA_CORE_PORT = int(_PORTS["krishna_core"])', config)
        self.assertIn('os.getenv("KRISHNA_PORT", str(KRISHNA_CORE_PORT))', config)
        self.assertNotIn('os.getenv("KRISHNA_PORT", "8766")', config)

    def test_live_powershell_paths_use_network_constants_loader(self):
        for rel in (
            "scripts/START_KRISHNA.ps1",
            "scripts/DEPLOY_KRISHNA_ONCE.ps1",
            "scripts/CONFIGURE_KRISHNA_PRIVATE_REMOTE_FIREWALL.ps1",
        ):
            text = (self.root / rel).read_text(encoding="utf-8")
            self.assertIn("KRISHNA_NETWORK_CONSTANTS.ps1", text, rel)
            self.assertIn("Get-KrishnaNetworkConstants", text, rel)

    def test_start_rejects_noncanonical_live_core_port(self):
        start = (self.root / "scripts" / "START_KRISHNA.ps1").read_text(encoding="utf-8")
        self.assertIn("KRISHNA live Core port is fixed", start)
        self.assertIn("$networkConstants.Core", start)


if __name__ == "__main__":
    unittest.main()
