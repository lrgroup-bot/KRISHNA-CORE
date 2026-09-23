from __future__ import annotations
import unittest

from krishna_core.avatar_runtime import AvatarRuntime

class AvatarRuntimeTests(unittest.TestCase):
    def test_all_character_states_are_expressible(self):
        a=AvatarRuntime()
        for state in ("FLUTE","IDLE","LISTENING","THINKING","SPEAKING","WISDOM","PLAYFUL","PROTECTION","DHYAN","SLEEPING","WAKING","WORKING"):
            out=a.set_state(state)
            self.assertEqual(out["state"],state)
            self.assertTrue(out["requires_rigged_glb"])

    def test_activity_maps_to_canonical_state(self):
        a=AvatarRuntime()
        self.assertEqual(a.for_activity("research")["state"],"THINKING")
        self.assertEqual(a.for_activity("repair")["state"],"WORKING")
        self.assertEqual(a.for_activity("security")["state"],"PROTECTION")

    def test_lipsync_does_not_claim_unrigged_fallback(self):
        a=AvatarRuntime()
        out=a.lip_sync(["viseme_aa","viseme_PP"])
        self.assertTrue(out["requires_morph_targets"])
        self.assertTrue(out["requires_rigged_glb"])

if __name__=="__main__":
    unittest.main()
