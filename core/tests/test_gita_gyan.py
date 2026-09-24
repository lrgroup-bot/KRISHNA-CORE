from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from krishna_core.gita_gyan import GitaDailyScheduler, GitaGyan


class GitaGyanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.catalog = root / "catalog.json"
        self.catalog.write_text(json.dumps({
            "schema": 1,
            "source_repository": "test",
            "source": "test",
            "license": "public-domain-test",
            "primary_translator": "test",
            "edition_note": "test edition",
            "verses": [
                {
                    "id": "BG1.1", "chapter": 1, "verse": 1,
                    "sanskrit": "श्लोक एक", "transliteration": "śloka eka",
                    "english": "Verse one.", "translator": "Test",
                },
                {
                    "id": "BG1.2", "chapter": 1, "verse": 2,
                    "sanskrit": "श्लोक द्वौ", "transliteration": "śloka dvau",
                    "english": "Verse two.", "translator": "Test",
                },
                {
                    "id": "BG2.47", "chapter": 2, "verse": 47,
                    "sanskrit": "कर्मण्येवाधिकारस्ते", "transliteration": "karmaṇyevādhikāraste",
                    "english": "You have a right to action.", "translator": "Test",
                },
            ],
        }, ensure_ascii=False), encoding="utf-8")
        self.root = root

    def tearDown(self):
        self.temp.cleanup()

    def test_daily_sequence_is_stable_per_day_and_does_not_repeat(self):
        gita = GitaGyan(self.root / "state", self.catalog)
        one = gita.daily_lesson("or", deep=False, for_date="2026-09-24")
        same = gita.daily_lesson("hi", deep=False, for_date="2026-09-24")
        two = gita.daily_lesson("or", deep=False, for_date="2026-09-25")
        self.assertEqual(one["id"], "BG1.1")
        self.assertEqual(same["id"], "BG1.1")
        self.assertEqual(two["id"], "BG1.2")
        self.assertEqual(gita.progress()["delivered_count"], 2)

    def test_public_text_is_separate_from_derived_explanation_and_cache(self):
        calls = []
        def explain(prompt):
            calls.append(prompt)
            return json.dumps({
                "literal_meaning": "ସରଳ ଅର୍ଥ",
                "context": "ପ୍ରସଙ୍ଗ",
                "deep_explanation": "ଗଭୀର ବ୍ୟାଖ୍ୟା",
                "practical_application": "ଦୈନିକ ପ୍ରୟୋଗ",
                "reflection_question": "ଆପଣ କ'ଣ ଭାବୁଛନ୍ତି?",
                "perspectives": [{"label": "textual", "explanation": "ପାଠ୍ୟ ଦୃଷ୍ଟି"}],
            }, ensure_ascii=False)

        gita = GitaGyan(self.root / "state", self.catalog, explainer=explain)
        first = gita.verse(2, 47, "or", deep=True)
        second = gita.verse(2, 47, "or", deep=True)
        self.assertEqual(first["sanskrit"], "कर्मण्येवाधिकारस्ते")
        self.assertFalse(first["canonical_text_mutable"])
        self.assertTrue(first["commentary_is_derived"])
        self.assertEqual(first["explanation"]["deep_explanation"], "ଗଭୀର ବ୍ୟାଖ୍ୟା")
        self.assertEqual(len(calls), 1)
        self.assertEqual(second["explanation"]["verse_id"], "BG2.47")

    def test_progress_questions_and_revision(self):
        gita = GitaGyan(self.root / "state", self.catalog)
        lesson = gita.daily_lesson("hi", deep=False, for_date="2026-09-24")
        marked = gita.mark_understood(lesson["id"], True, "clear")
        asked = gita.add_question(lesson["id"], "How does this apply today?")
        revision = gita.revision("hi", 7, deep=False)
        self.assertTrue(marked["understood"])
        self.assertEqual(asked["verse_id"], lesson["id"])
        self.assertEqual(revision["count"], 1)
        self.assertEqual(gita.progress()["understood_count"], 1)

    def test_command_parser_selects_language_depth_revision_and_reference(self):
        gita = GitaGyan(self.root / "state", self.catalog)
        daily = gita.interpret_command("Krishna today's Gita Odia re deeply bujhaa")
        revision = gita.interpret_command("Yesterday verse revise in Hindi")
        exact = gita.interpret_command("Chapter 2 shloka 47 Hindi deeply")
        self.assertEqual((daily["intent"], daily["language"], daily["deep"]), ("daily", "or", True))
        self.assertEqual((revision["intent"], revision["language"]), ("revision", "hi"))
        self.assertEqual((exact["intent"], exact["chapter"], exact["verse"], exact["language"]), ("verse", 2, 47, "hi"))

    def test_scheduler_runs_once_after_configured_time(self):
        calls = []
        scheduler = GitaDailyScheduler(
            lambda: calls.append("ran") or {"ok": True},
            daily_time="07:30",
            timezone_name="Asia/Kolkata",
            enabled=True,
        )
        tz = scheduler.timezone
        self.assertEqual(scheduler.run_due(datetime(2026, 9, 24, 7, 29, tzinfo=tz))["status"], "not_due")
        self.assertEqual(scheduler.run_due(datetime(2026, 9, 24, 7, 30, tzinfo=tz))["status"], "completed")
        self.assertEqual(scheduler.run_due(datetime(2026, 9, 24, 20, 0, tzinfo=tz))["status"], "already_ran")
        self.assertEqual(calls, ["ran"])

    def test_invalid_language_and_missing_verse_are_rejected(self):
        gita = GitaGyan(self.root / "state", self.catalog)
        with self.assertRaises(ValueError):
            gita.set_language("fr")
        with self.assertRaises(KeyError):
            gita.verse(99, 1)


if __name__ == "__main__":
    unittest.main()
