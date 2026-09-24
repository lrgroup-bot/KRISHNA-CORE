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

    def test_odia_is_global_default_conversation_language(self):
        status=KrishnaCharacterPersona.status()
        self.assertEqual(status["default_conversation_language"],"or")
        self.assertEqual(status["default_conversation_locale"],"or-IN")
        self.assertTrue(status["global_odia_default"])
        prompt=KrishnaCharacterPersona.prompt_contract()
        self.assertIn("Global default conversation language is natural Odia",prompt)

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


class WiringContractTests(unittest.TestCase):
    def test_avatar_fabric_accepts_canonical_gita_state_commands(self):
        from krishna_core.avatar_fabric import AvatarFabric
        avatar=AvatarFabric()
        out=avatar.set_state("WISDOM",source="gita-test",performance_id="gita-02-047")
        self.assertEqual(out["state"],"WISDOM")
        self.assertEqual(out["params"]["performance_id"],"gita-02-047")
        self.assertFalse(out["visible_animation_verified"])

    def test_avatar_fabric_exposes_partha_and_scripture_style(self):
        text=(Path(__file__).resolve().parents[1]/"krishna_core"/"avatar_fabric.py").read_text(encoding="utf-8-sig")
        self.assertIn('OWNER_ADDRESS="Partha"',text)
        self.assertIn("SCRIPTURE_GROUNDED_STYLE",text)
        self.assertIn("bhagavad_gita_18_63",text)

    def test_orchestrator_injects_character_contract(self):
        text=(Path(__file__).resolve().parents[1]/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8-sig")
        self.assertIn("self.agi.character.prompt_contract()",text)
        self.assertIn("self.agi.character.address_rule()",text)

    def test_http_runtime_exposes_character_age_and_wake_reply(self):
        text=(Path(__file__).resolve().parents[1]/"krishna_core"/"server.py").read_text(encoding="utf-8-sig")
        self.assertIn('"/api/character"',text)
        self.assertIn('"/api/avatar/age"',text)
        self.assertIn('"/api/avatar/age/configure"',text)
        self.assertIn('payload["reply_text"]=orch.agi.character.ODIA_WAKE',text)


if __name__=="__main__":
    unittest.main()
