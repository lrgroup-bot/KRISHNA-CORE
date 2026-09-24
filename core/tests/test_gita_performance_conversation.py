from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from krishna_core.avatar_runtime import AvatarRuntime
from krishna_core.gita_gyan import GitaGyan
from krishna_core.gita_performance import GitaPerformanceEngine
from krishna_core.krishna_shloka import KrishnaShlokaOrchestrator


class GitaPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.gita = GitaGyan(Path(self.temp.name) / "gita")
        self.performance = GitaPerformanceEngine(self.gita)

    def tearDown(self):
        self.temp.cleanup()

    def test_every_canonical_verse_has_one_valid_performance_record(self):
        report = self.performance.qc_report()
        self.assertTrue(report["valid"], report["failures"][:10])
        self.assertEqual(report["record_count"], 700)
        self.assertEqual(report["unique_verse_count"], 700)
        self.assertEqual(report["expected_verse_count"], 700)

    def test_required_fields_exist_without_fabricating_missing_translations(self):
        record = self.performance.record(1, 1)
        for field in GitaPerformanceEngine.REQUIRED_FIELDS:
            self.assertIn(field, record)
        self.assertIsNone(record["meaning_or"])
        self.assertIsNone(record["meaning_hi"])
        self.assertIsNone(record["meaning_en"])
        self.assertTrue(record["sanskrit"].strip())
        self.assertTrue(record["scriptural_evidence"])

    def test_gita_2_10_is_restrained_smiling_teacher(self):
        record = self.performance.record(2, 10)
        self.assertEqual(record["avatar_family"], "SMILING_TEACHER")
        self.assertLess(record["smile_level"], 0.5)
        self.assertIn("reassuring", record["face_expression"])
        self.assertTrue(record["manual_override"])

    def test_gita_2_47_is_karma_yoga_teacher(self):
        record = self.performance.record(2, 47)
        self.assertEqual(record["avatar_family"], "KARMA_YOGA_TEACHER")
        self.assertIn("action", record["theme"])
        self.assertIn("results", record["theme"])
        self.assertEqual(record["partha_dialogue_profile"]["address"], "Partha")

    def test_vishvarupa_is_cosmic_only_in_supported_chapter_11_passage(self):
        record = self.performance.record(11, 32)
        self.assertEqual(record["avatar_family"], "VISHVARUPA")
        self.assertEqual(record["krishna_form"], "vishvarupa_cosmic")
        self.assertEqual(record["camera_profile"], "COSMIC_REVEAL")
        self.assertEqual(record["background_profile"], "COSMIC_VISHVARUPA")
        self.assertFalse(self.performance.validate_record(record))

    def test_chapter_11_returns_to_reassuring_personal_form(self):
        for verse in (50, 51):
            record = self.performance.record(11, verse)
            self.assertEqual(record["avatar_family"], "REASSURING_PERSONAL_FORM")
            self.assertEqual(record["camera_profile"], "RETURN_TO_HUMAN_FORM")
            self.assertEqual(record["krishna_form"], "personal_form_return")

    def test_gita_18_63_preserves_partha_agency(self):
        record = self.performance.record(18, 63)
        self.assertEqual(record["avatar_family"], "CLOSING_COUNSEL")
        self.assertIn("choose", record["theme"])
        self.assertTrue(record["partha_dialogue_profile"]["preserve_agency"])
        textual = [x for x in record["scriptural_evidence"] if x["kind"] == "TEXTUAL_FACT"]
        self.assertTrue(any("reflect fully" in x["detail"] for x in textual))

    def test_animation_choice_is_not_misrepresented_as_scripture(self):
        record = self.performance.record(2, 47)
        kinds = {x["kind"] for x in record["scriptural_evidence"]}
        self.assertIn("TEXTUAL_FACT", kinds)
        self.assertIn("ANIMATION_DESIGN_DECISION", kinds)


class KrishnaShlokaConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.gita = GitaGyan(root / "gita")
        self.performance = GitaPerformanceEngine(self.gita)
        self.shloka = KrishnaShlokaOrchestrator(
            self.gita, self.performance, root / "conversation.json"
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_2_47_preserves_canonical_sanskrit_and_separates_commentary(self):
        out = self.shloka.parse_request(
            "Krishna, explain Gita 2.47 in Odia deeply",
            explain=lambda prompt: "ପାର୍ଥ, ଏହା ଏକ ବ୍ୟାଖ୍ୟା।",
        )
        self.assertEqual(out["reference"], "Bhagavad Gita 2.47")
        self.assertIn("कर्मण्येवाधिकारस्ते", out["sanskrit"])
        self.assertEqual(out["language"], "or")
        self.assertEqual(out["generated_explanation"], "ପାର୍ଥ, ଏହା ଏକ ବ୍ୟାଖ୍ୟା।")
        self.assertTrue(out["canonical_sanskrit_unchanged"])
        self.assertTrue(out["generated_commentary_separate"])
        self.assertEqual(out["speech_segments"][0]["mode"], "SHLOKA_RECITATION")

    def test_situation_confusion_selects_curated_verified_verse(self):
        out = self.shloka.parse_request("Krishna, I am confused")
        self.assertEqual(out["reference"], "Bhagavad Gita 2.7")
        self.assertEqual(out["selection"]["category"], "confusion")
        self.assertIn("not a claim of divine certainty", out["selection"]["reason"])

    def test_work_theme_search_can_find_2_47(self):
        result = self.shloka.search("work results", limit=20)
        refs = {x["reference"] for x in result["items"]}
        self.assertIn("Bhagavad Gita 2.47", refs)

    def test_chapter_request_returns_complete_chapter(self):
        out = self.shloka.parse_request("Krishna, recite chapter 12")
        self.assertEqual(out["chapter"], 12)
        self.assertEqual(out["verse_count"], 20)
        self.assertEqual(len(out["items"]), 20)

    def test_next_and_previous_verse_use_persistent_conversation_state(self):
        self.shloka.parse_request("Gita 2.47")
        nxt = self.shloka.parse_request("next verse")
        self.assertEqual(nxt["reference"], "Bhagavad Gita 2.48")
        prev = self.shloka.parse_request("previous verse")
        self.assertEqual(prev["reference"], "Bhagavad Gita 2.47")

    def test_direct_partha_line_never_uses_forbidden_owner_titles(self):
        out = self.shloka.verse(11, 51, language="en")
        self.assertIn("Partha", out["partha_line"])
        for forbidden in ("Arjuna", "Arjun", "Sir", "Boss", "Master"):
            self.assertNotIn(forbidden, out["partha_line"])


class AvatarGitaPerformanceTests(unittest.TestCase):
    def test_avatar_runtime_applies_vishvarupa_and_return_transition_without_claiming_asset_ready(self):
        with tempfile.TemporaryDirectory() as td:
            gita = GitaGyan(Path(td) / "gita")
            performance = GitaPerformanceEngine(gita)
            avatar = AvatarRuntime()
            cosmic = avatar.apply_performance(performance.record(11, 32))
            self.assertEqual(cosmic["renderer_mode"], "cosmic_vishvarupa")
            self.assertTrue(cosmic["requires_cosmic_layer"])
            self.assertTrue(cosmic["requires_rigged_glb"])
            returned = avatar.apply_performance(performance.record(11, 50))
            self.assertEqual(returned["renderer_mode"], "personal_krishna")
            self.assertEqual(returned["transition_from"], "VISHVARUPA")
            self.assertEqual(returned["transition_to"], "REASSURING_PERSONAL_FORM")
            self.assertIn("not VERIFIED", avatar.status()["asset_policy"])


class GitaApiContractTests(unittest.TestCase):
    def test_server_exposes_complete_gita_api_contract(self):
        text = (Path(__file__).resolve().parents[1] / "krishna_core" / "server.py").read_text(encoding="utf-8-sig")
        for token in (
            '"/api/gita/verse/"',
            '"/api/gita/chapter/"',
            '"/api/gita/search"',
            '"/api/gita/explain"',
            '"/api/gita/speak"',
            '"/api/gita/performance/"',
            '"/api/gita/performance/apply"',
            '"/api/gita/performance/qc"',
            '"/api/character"',
            '"/api/avatar/age"',
            '"/api/avatar/performance"',
            '"/api/avatar/status"',
        ):
            self.assertIn(token, text)

    def test_orchestrator_uses_one_canonical_gita_and_avatar_runtime(self):
        text = (Path(__file__).resolve().parents[1] / "krishna_core" / "orchestrator.py").read_text(encoding="utf-8-sig")
        self.assertIn("self.gita_performance = GitaPerformanceEngine(self.gita_gyan)", text)
        self.assertIn("self.gita_shloka = KrishnaShlokaOrchestrator(self.gita_gyan, self.gita_performance", text)
        self.assertIn("self.agi.avatar.apply_performance(performance)", text)

    def test_mobile_remote_policy_allows_gita_conversation_routes(self):
        text = (Path(__file__).resolve().parents[1] / "krishna_core" / "remote_access.py").read_text(encoding="utf-8-sig")
        self.assertIn('"/api/gita/search"', text)
        self.assertIn('"/api/gita/explain"', text)
        self.assertIn('"/api/gita/speak"', text)
        self.assertIn('"/api/gita/verse/"', text)


if __name__ == "__main__":
    unittest.main()
