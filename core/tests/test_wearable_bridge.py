import tempfile
import unittest
from pathlib import Path

from krishna_core.wearable_bridge import WearableBridge


class WearableBridgeTests(unittest.TestCase):
    def test_declared_capability_is_not_verified_by_registration(self):
        with tempfile.TemporaryDirectory() as td:
            bridge=WearableBridge(Path(td)/"wearables.json")
            row=bridge.register("Test Glass","glasses",["camera","ar_display","gesture"])
            self.assertFalse(row["verified"])
            self.assertEqual(row["verified_capabilities"],[])

    def test_verification_is_capability_specific(self):
        with tempfile.TemporaryDirectory() as td:
            bridge=WearableBridge(Path(td)/"wearables.json")
            row=bridge.register("Test Glass","glasses",["camera","ar_display","gesture"])
            verified=bridge.verify(row["id"],["camera"],evidence="real camera adapter test")
            self.assertEqual(verified["verified_capabilities"],["camera"])
            self.assertNotIn("ar_display",verified["verified_capabilities"])
            with self.assertRaises(PermissionError):
                bridge.observe(row["id"],"gesture",{"gesture":"pinch"})
            packet=bridge.observe(row["id"],"camera",{"frame_ref":"local:1"})
            self.assertTrue(packet["hardware_verified"])

    def test_ar_display_and_head_tracking_are_valid_declared_caps(self):
        with tempfile.TemporaryDirectory() as td:
            row=WearableBridge(Path(td)/"wearables.json").register(
                "XR Bridge","glasses",["ar_display","head_tracking"]
            )
            self.assertIn("ar_display",row["capabilities"])
            self.assertIn("head_tracking",row["capabilities"])


if __name__=="__main__":
    unittest.main()
