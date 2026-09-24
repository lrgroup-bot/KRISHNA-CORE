from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from krishna_core.avatar_age_profile import AvatarAgeProfile
from krishna_core.character_persona import KrishnaCharacterPersona


class KrishnaPersonaTests(unittest.TestCase):
    def test_owner_is_only_partha(self):
        status=KrishnaCharacterPersona.status()
        self.assertEqual(status["owner_address"],"Partha")
        self.assertIn("Arjuna",status["forbidden_owner_addresses"])
        prompt=KrishnaCharacterPersona.prompt_contract()
        self.assertIn("use only 'Partha'",prompt)
        self.assertIn("କୁହ ପାର୍ଥ, କଣ ହେଲା?",prompt)

    def test_scripture_grounding_is_explicit(self):
        refs=KrishnaCharacterPersona.status()["scripture_grounding"]
        self.assertIn("bhagavad_gita_2_10",refs)
        self.assertIn("bhagavad_gita_11_50",refs)
        self.assertIn("bhagavad_gita_18_63",refs)
        self.assertIn("bhagavata_purana_10_30_2_3",refs)


class AvatarAgeProfileTests(unittest.TestCase):
    def test_daily_age_progression_is_deterministic_and_private(self):
        with tempfile.TemporaryDirectory() as td:
            profile=AvatarAgeProfile(Path(td))
            profile.configure(
                baseline_date="2026-01-01",
                base_visual_age_years=5.0,
                growth_rate_days_per_day=1.0,
            )
            out=profile.status(date(2026,1,11))
            self.assertEqual(out["real_days_elapsed"],10)
            self.assertEqual(out["visual_age_offset_days"],10.0)
            self.assertGreater(out["display_visual_age_years"],5.0)
            self.assertTrue(out["identity_lock"])
            self.assertFalse(out["cloud_upload_allowed"])
            self.assertFalse(out["renderer_ready"])

    def test_age_controller_does_not_need_real_child_birth_date(self):
        with tempfile.TemporaryDirectory() as td:
            profile=AvatarAgeProfile(Path(td))
            out=profile.status()
            self.assertIsNone(out["base_visual_age_years"])
            self.assertEqual(out["identity_mode"],"private_child_likeness")
            self.assertTrue(out["daily_progression"])


if __name__=="__main__":
    unittest.main()
