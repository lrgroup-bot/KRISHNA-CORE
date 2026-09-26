import unittest

from krishna_core.capability_fabric import build_default_capability_fabric


class CapabilityFabricTests(unittest.TestCase):
    def test_mobile_conversation_prefers_direct_short_lived_cloud(self):
        fabric=build_default_capability_fabric()
        row=fabric.choose("conversation",require_free=True,prefer_mobile=True)
        self.assertEqual(row["provider_id"],"gemini-live-ephemeral")
        self.assertTrue(row["mobile_direct"])
        self.assertTrue(row["lazy"])

    def test_heavy_dots_model_is_dormant(self):
        fabric=build_default_capability_fabric()
        dots=[x for x in fabric.list("multimodal-large") if x["provider_id"]=="dots3-note-prev"][0]
        self.assertFalse(dots["enabled"])
        self.assertTrue(dots["lazy"])
        self.assertFalse(fabric.status()["always_on_heavy_runtime"])

    def test_pc_vision_remains_available_for_private_heavy_escalation(self):
        fabric=build_default_capability_fabric()
        rows={x["provider_id"]:x for x in fabric.list("vision")}
        self.assertIn("krishna-pc-vision",rows)
        self.assertTrue(rows["krishna-pc-vision"]["local"])


if __name__=="__main__":
    unittest.main()
