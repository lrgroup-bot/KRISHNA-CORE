from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from krishna_core.avatar_runtime import AvatarRuntime
from krishna_core.gita_gyan import GitaGyan
from krishna_core.gita_performance import GitaPerformanceEngine
from krishna_core.krishna_shloka import KrishnaShlokaOrchestrator
from krishna_core.lip_sync import (
    KrishnaLipSyncPlanner,
    OCULUS_VISEMES,
    OCULUS_MORPH_TARGETS,
)


class KrishnaLipSyncPlannerTests(unittest.TestCase):
    def test_supports_sanskrit_odia_hindi_english(self):
        samples = {
            "sa": "कर्मण्येवाधिकारस्ते",
            "or": "କୁହ ପାର୍ଥ",
            "hi": "पार्थ, अब समझते हैं",
            "en": "Partha, consider this calmly.",
        }
        for language, text in samples.items():
            plan = KrishnaLipSyncPlanner.plan(text, language)
            self.assertGreater(plan["duration_ms"], 0)
            self.assertTrue(plan["events"])
            self.assertEqual(plan["events"][-1]["viseme"], "sil")
            self.assertFalse(plan["acoustic_alignment_verified"])
            self.assertTrue(plan["requires_audio_alignment_for_production"])
            for event in plan["events"]:
                self.assertIn(event["viseme"], OCULUS_VISEMES)
                self.assertEqual(event["morph_target"], OCULUS_MORPH_TARGETS[event["viseme"]])
                self.assertTrue(event["morph_target"].startswith("viseme_"))
                self.assertLessEqual(event["start_ms"], event["end_ms"])

    def test_shloka_profile_is_slower_than_explanation(self):
        text = "कर्म"
        shloka = KrishnaLipSyncPlanner.plan(text, "sa", "SHLOKA_RECITATION")
        prose = KrishnaLipSyncPlanner.plan(text, "sa", "GITA_EXPLANATION")
        self.assertGreater(shloka["duration_ms"], prose["duration_ms"])

    def test_empty_text_is_safe(self):
        plan = KrishnaLipSyncPlanner.plan("", "or")
        self.assertEqual(plan["duration_ms"], 0)
        self.assertEqual(plan["events"], [])

    def test_avatar_runtime_exposes_truthful_text_to_viseme_plan(self):
        out = AvatarRuntime().plan_lip_sync("ପାର୍ଥ", "or", "KRISHNA_TO_PARTHA")
        self.assertEqual(out["action"], "talk")
        self.assertTrue(out["requires_rigged_glb"])
        self.assertTrue(out["requires_morph_targets"])
        self.assertFalse(out["acoustic_alignment_verified"])
        self.assertTrue(out["lip_sync"]["events"])


class GitaLipSyncIntegrationTests(unittest.TestCase):
    def test_gita_247_has_lip_sync_for_shloka_and_partha_dialogue(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gita = GitaGyan(root / "gita")
            perf = GitaPerformanceEngine(gita)
            shloka = KrishnaShlokaOrchestrator(gita, perf, root / "conversation.json")
            out = shloka.verse(2, 47, language="or", explain=lambda _: "କାମ କର, ଫଳରେ ଆସକ୍ତ ହେଅ ନାହିଁ।")
            segments = out["speech_segments"]
            self.assertEqual(segments[0]["language"], "sa")
            self.assertEqual(segments[0]["lip_sync"]["mode"], "SHLOKA_RECITATION")
            self.assertTrue(segments[0]["lip_sync"]["events"])
            self.assertEqual(segments[1]["language"], "or")
            self.assertTrue(segments[1]["lip_sync"]["events"])
            self.assertEqual(segments[2]["mode"], "KRISHNA_TO_PARTHA")
            self.assertTrue(segments[2]["lip_sync"]["events"])


if __name__ == "__main__":
    unittest.main()
