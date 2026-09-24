from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from krishna_core.gita_gyan import GitaGyan


class GitaGyanTests(unittest.TestCase):
    def test_daily_lesson_is_deterministic_per_day_and_uses_wisdom_avatar(self):
        with tempfile.TemporaryDirectory() as td:
            gita = GitaGyan(Path(td))
            first = gita.daily_lesson(language="or", on_date=date(2026, 9, 24))
            again = gita.daily_lesson(language="or", on_date=date(2026, 9, 24))
            self.assertEqual(first["reference"], again["reference"])
            self.assertEqual(first["avatar_state"], "WISDOM")
            self.assertEqual(first["language"], "or")

    def test_progress_advances_on_next_day_without_repeating(self):
        with tempfile.TemporaryDirectory() as td:
            gita = GitaGyan(Path(td))
            first = gita.daily_lesson(on_date=date(2026, 9, 24))
            second = gita.daily_lesson(on_date=date(2026, 9, 25))
            self.assertNotEqual(first["reference"], second["reference"])

    def test_scripture_and_commentary_are_separate(self):
        with tempfile.TemporaryDirectory() as td:
            gita = GitaGyan(Path(td))
            out = gita.daily_lesson(
                language="hi",
                explain=lambda prompt: "यह व्याख्या है।",
                on_date=date(2026, 9, 24),
            )
            self.assertIn("कर्मण्येवाधिकारस्ते", out["sanskrit"])
            self.assertEqual(out["explanation"], "यह व्याख्या है।")
            self.assertNotEqual(out["sanskrit"], out["explanation"])

    def test_deep_prompt_preserves_agency_and_tradition_differences(self):
        with tempfile.TemporaryDirectory() as td:
            gita = GitaGyan(Path(td))
            row = gita.verse(2, 47)
            prompt = gita.lesson_prompt(row, "or", "deep")
            self.assertIn("Preserve Partha's agency", prompt)
            self.assertIn("traditions differ", prompt)
            self.assertIn(row["sanskrit"], prompt)

    def test_complete_corpus_contract_uses_700_verse_canonical_count(self):
        self.assertEqual(sum(GitaGyan.CHAPTER_VERSE_COUNTS), 700)
        with tempfile.TemporaryDirectory() as td:
            status = GitaGyan(Path(td)).status()
            self.assertEqual(status["expected_verses"], 700)
            self.assertFalse(status["corpus_complete"])

    def test_import_corpus_validates_chapter_and_verse_ranges(self):
        with tempfile.TemporaryDirectory() as td:
            gita = GitaGyan(Path(td))
            result = gita.import_corpus([
                {"chapter": 1, "verse": 1, "sanskrit": "धर्मक्षेत्रे कुरुक्षेत्रे"},
                {"chapter": 19, "verse": 1, "sanskrit": "invalid"},
            ])
            self.assertEqual(result["imported"], 1)
            self.assertEqual(gita.verse(1, 1)["chapter"], 1)


class GitaWiringContractTests(unittest.TestCase):
    def test_orchestrator_wires_gita_runtime(self):
        text = (Path(__file__).resolve().parents[1] / "krishna_core" / "orchestrator.py").read_text(encoding="utf-8-sig")
        self.assertIn("from .gita_gyan import GitaGyan", text)
        self.assertIn("self.gita_gyan = GitaGyan", text)
        self.assertIn("def gita_daily_lesson", text)

    def test_server_exposes_gita_routes(self):
        text = (Path(__file__).resolve().parents[1] / "krishna_core" / "server.py").read_text(encoding="utf-8-sig")
        self.assertIn('"/api/gita/status"', text)
        self.assertIn('"/api/gita/today"', text)
        self.assertIn('"/api/gita/revise"', text)

    def test_mobile_policy_allows_gita_learning_routes(self):
        text = (Path(__file__).resolve().parents[1] / "krishna_core" / "remote_access.py").read_text(encoding="utf-8-sig")
        self.assertIn('"/api/gita/status"', text)
        self.assertIn('"/api/gita/today"', text)
        self.assertIn('"/api/gita/revise"', text)


if __name__ == "__main__":
    unittest.main()
