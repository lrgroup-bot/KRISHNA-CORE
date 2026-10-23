"""Fast/slow browser-video playback must be evidence-conservative."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ADAPTER = Path(__file__).resolve().parents[3] / "scripts" / "SURYDEV_VIDEO_LEARNING_ADAPTER.py"
spec = importlib.util.spec_from_file_location("suryadev_speed_adapter_test", ADAPTER)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class AdaptiveVideoSpeedTests(unittest.TestCase):
    def test_critical_technical_and_math_slow_to_1x(self):
        for caption in (
            "Step 1: install Python 3.12",
            "WARNING: never plug the live voltage connector",
            "Algorithm is O(n^2)",
            "Remember this security configuration",
            "Here is a working example",
        ):
            with self.subTest(caption=caption):
                self.assertEqual(adapter.classify_video_caption(caption)[1], 1.0)

    def test_teaching_gets_one_point_five(self):
        self.assertEqual(adapter.classify_video_caption("This works because of the parser"),
                         ("explanation", 1.5))

    def test_generic_clear_caption_gets_2x(self):
        self.assertEqual(adapter.classify_video_caption("The session continues as expected"),
                         ("ordinary", 2.0))

    def test_unknown_odia_hindi_and_other_scripts_default_to_one(self):
        for caption in ("यहाँ एक महत्वपूर्ण बात है", "ଏହା ବହୁତ ଜରୁରୀ", "これは大切です"):
            with self.subTest(caption=caption):
                self.assertEqual(adapter.classify_video_caption(caption),
                                 ("unclassified_language", 1.0))

    def test_chatter_needs_two_distinct_segments_before_4x(self):
        p = adapter.AdaptiveVideoSpeed()
        self.assertEqual(p.choose("Welcome back to my channel",
                                  video_seconds=1, caption_available=True)[0], 2.0)
        self.assertEqual(p.choose("Like and subscribe to the channel",
                                  video_seconds=3, caption_available=True), (4.0, "chatter"))
        self.assertEqual(p.choose("This is an important Python 3.12 example",
                                  video_seconds=4, caption_available=True), ("important", 1.0))
        self.assertEqual(p.chatter_streak, 0)

    def test_chatter_with_technical_keywords_stays_important(self):
        p = adapter.AdaptiveVideoSpeed()
        self.assertEqual(p.choose("Hey everyone, I have a warning about memory voltage",
                                  video_seconds=1, caption_available=True)[0], 1.0)
        self.assertEqual(p.choose("Let me know in the comments about the algorithm",
                                  video_seconds=2, caption_available=True)[0], 1.0)

    def test_missing_captions_and_asr_do_not_speed_up(self):
        p = adapter.AdaptiveVideoSpeed()
        self.assertEqual(p.choose("Hello everyone", video_seconds=1,
                                  caption_available=False)[0], 1.0)
        self.assertEqual(p.choose("Hello everyone", video_seconds=2,
                                  caption_available=True, asr_active=True)[0], 1.0)
        p.choose("Welcome back", video_seconds=3, caption_available=True)
        p.choose("Like and subscribe", video_seconds=4, caption_available=True)
        self.assertEqual(p.choose("", video_seconds=7, caption_available=False)[0], 1.0)

    def test_stalled_caption_reverts_to_one(self):
        p = adapter.AdaptiveVideoSpeed()
        p.choose("Welcome back", video_seconds=0, caption_available=True)
        p.choose("Like and subscribe", video_seconds=2, caption_available=True)
        self.assertEqual(p.choose("Like and subscribe",
                                  video_seconds=7.5, caption_available=True),
                         (1.0, "caption_stalled"))

    def test_owner_capture_term_forces_1x(self):
        p = adapter.AdaptiveVideoSpeed(("solar panel",))
        self.assertEqual(p.choose("The solar panel does the work",
                                  video_seconds=5, caption_available=True)[0], 1.0)

    def test_disabled_mode_uses_1x(self):
        p = adapter.AdaptiveVideoSpeed(enabled=False)
        self.assertEqual(p.choose("Like and subscribe",
                                  video_seconds=4, caption_available=True)[0], 1.0)

    def test_readback_is_used_not_unverified_requested_speed(self):
        class FakePage:
            def __init__(self, response):
                self.response = response
                self.attempts = []
            def evaluate(self, script, requested):
                self.attempts.append(requested)
                return self.response
        page = FakePage(2.0)
        self.assertEqual(adapter._apply_video_rate(page, 4.0), 2.0)
        self.assertEqual(page.attempts, [4.0])
        self.assertIsNone(adapter._apply_video_rate(FakePage(None), 4.0))
        self.assertIsNone(adapter._apply_video_rate(FakePage(1.25), 1.5))


if __name__ == "__main__":
    unittest.main()
