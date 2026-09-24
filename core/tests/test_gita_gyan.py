from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from krishna_core.gita_gyan import GitaGyan
from krishna_core.gita_performance import GitaPerformanceEngine
from krishna_core.krishna_shloka import KrishnaShlokaOrchestrator
from krishna_core.character_persona import KrishnaCharacterPersona
from krishna_core.native_voice import KrishnaVoiceStack


class GitaGyanTests(unittest.TestCase):
    def test_bundled_corpus_is_complete_700_verse_recension(self):
        with tempfile.TemporaryDirectory() as td:
            gita = GitaGyan(Path(td))
            status = gita.status()
            self.assertEqual(status["available_verses"], 700)
            self.assertEqual(status["expected_verses"], 700)
            self.assertTrue(status["corpus_complete"])
            self.assertTrue(status["integrity"]["chapter_counts_match"])
            self.assertEqual(status["integrity"]["unique_reference_count"], 700)
            self.assertEqual(status["corpus_mode"], "bundled")
            self.assertEqual(status["recension"], "conventional-700-verse")

    def test_all_18_chapter_counts_match_canonical_700_contract(self):
        self.assertEqual(sum(GitaGyan.CHAPTER_VERSE_COUNTS), 700)
        with tempfile.TemporaryDirectory() as td:
            status = GitaGyan(Path(td)).status()
            counts = status["integrity"]["chapter_counts"]
            for chapter, expected in enumerate(GitaGyan.CHAPTER_VERSE_COUNTS, start=1):
                self.assertEqual(int(counts[chapter]), expected)

    def test_daily_lesson_is_deterministic_per_day_and_uses_wisdom_avatar(self):
        with tempfile.TemporaryDirectory() as td:
            gita = GitaGyan(Path(td))
            first = gita.daily_lesson(language="or", on_date=date(2026, 9, 24))
            again = gita.daily_lesson(language="or", on_date=date(2026, 9, 24))
            self.assertEqual(first["reference"], again["reference"])
            self.assertEqual(first["reference"], "Bhagavad Gita 1.1")
            self.assertEqual(first["avatar_state"], "WISDOM")
            self.assertEqual(first["language"], "or")
            self.assertTrue(first["corpus_complete"])

    def test_progress_advances_on_next_day_without_repeating(self):
        with tempfile.TemporaryDirectory() as td:
            gita = GitaGyan(Path(td))
            first = gita.daily_lesson(on_date=date(2026, 9, 24))
            second = gita.daily_lesson(on_date=date(2026, 9, 25))
            self.assertEqual(first["reference"], "Bhagavad Gita 1.1")
            self.assertEqual(second["reference"], "Bhagavad Gita 1.2")

    def test_scripture_and_commentary_are_separate(self):
        with tempfile.TemporaryDirectory() as td:
            gita = GitaGyan(Path(td))
            out = gita.daily_lesson(
                language="hi",
                explain=lambda prompt: "यह व्याख्या है।",
                on_date=date(2026, 9, 24),
            )
            self.assertTrue(out["sanskrit"].strip())
            self.assertEqual(out["explanation"], "यह व्याख्या है।")
            self.assertNotEqual(out["sanskrit"], out["explanation"])

    def test_deep_prompt_preserves_agency_and_tradition_differences(self):
        with tempfile.TemporaryDirectory() as td:
            gita = GitaGyan(Path(td))
            row = gita.verse(2, 47)
            self.assertIn("कर्मण्येवाधिकारस्ते", row["sanskrit"])
            prompt = gita.lesson_prompt(row, "or", "deep")
            self.assertIn("Preserve Partha's agency", prompt)
            self.assertIn("traditions differ", prompt)
            self.assertIn(row["sanskrit"], prompt)

    def test_chapter_13_normalization_uses_conventional_34_verse_numbering(self):
        with tempfile.TemporaryDirectory() as td:
            gita = GitaGyan(Path(td))
            first = gita.verse(13, 1)
            last = gita.verse(13, 34)
            self.assertIn("इदं शरीरं", first["sanskrit"])
            self.assertEqual(first["source"]["source_chapter"], 13)
            self.assertEqual(first["source"]["source_verse"], 2)
            self.assertEqual(last["source"]["source_verse"], 35)
            with self.assertRaises(KeyError):
                gita.verse(13, 35)

    def test_provenance_is_pinned_and_unlicensed_source_is_declared(self):
        with tempfile.TemporaryDirectory() as td:
            status = GitaGyan(Path(td)).status()
            provenance = status["provenance"]
            self.assertEqual(provenance["source_repository"], "https://github.com/gita/gita")
            self.assertEqual(provenance["source_file"], "data/verse.json")
            self.assertEqual(provenance["license"], "Unlicense")
            self.assertEqual(len(provenance["source_commit"]), 40)
            self.assertEqual(len(status["corpus_sha256"]), 64)

    def test_runtime_override_does_not_rewrite_bundled_scripture(self):
        with tempfile.TemporaryDirectory() as td:
            gita = GitaGyan(Path(td))
            bundled = gita.bundled_corpus_path.read_bytes()
            result = gita.import_corpus([
                {"chapter": 1, "verse": 1, "sanskrit": "धर्मक्षेत्रे कुरुक्षेत्रे"},
                {"chapter": 19, "verse": 1, "sanskrit": "invalid"},
            ])
            self.assertEqual(result["imported"], 1)
            self.assertFalse(result["complete"])
            self.assertEqual(gita.status()["corpus_mode"], "runtime_override")
            self.assertEqual(gita.bundled_corpus_path.read_bytes(), bundled)
            restored = gita.clear_runtime_override()
            self.assertTrue(restored["corpus_complete"])
            self.assertEqual(restored["corpus_mode"], "bundled")

    def test_bundled_json_contains_exactly_700_unique_references(self):
        path = Path(__file__).resolve().parents[1] / "krishna_core" / "data" / "bhagavad_gita_700.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        verses = payload["verses"]
        refs = {(int(x["chapter"]), int(x["verse"])) for x in verses}
        self.assertEqual(len(verses), 700)
        self.assertEqual(len(refs), 700)
        self.assertEqual(payload["verse_count"], 700)


class GitaConversationSessionTests(unittest.TestCase):
    def _runtime(self, root):
        gita=GitaGyan(Path(root))
        perf=GitaPerformanceEngine(gita)
        return KrishnaShlokaOrchestrator(gita,perf,Path(root)/"conversation.json")

    def test_one_verse_at_a_time_never_auto_advances(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=self._runtime(td)
            first=runtime.verse(2,47,language="or",explain=None)
            self.assertEqual(first["reference"],"Bhagavad Gita 2.47")
            self.assertTrue(first["one_verse_at_a_time"])
            self.assertFalse(first["auto_advance"])
            self.assertTrue(first["awaiting_owner_control"])
            self.assertEqual(runtime.session_status()["current_reference"],"2.47")

    def test_repeat_next_previous_controls_are_persistent(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=self._runtime(td)
            runtime.verse(2,47,language="or",explain=None)
            repeated=runtime.control("repeat",explain=None)
            self.assertEqual(repeated["reference"],"Bhagavad Gita 2.47")
            nxt=runtime.control("next",explain=None)
            self.assertEqual(nxt["reference"],"Bhagavad Gita 2.48")
            prev=runtime.control("previous",explain=None)
            self.assertEqual(prev["reference"],"Bhagavad Gita 2.47")

    def test_next_marks_current_complete_but_repeat_does_not_advance(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=self._runtime(td)
            runtime.verse(2,47,language="or",explain=None)
            self.assertFalse(runtime.session_status()["current_completed"])
            repeated=runtime.control("repeat",explain=None)
            self.assertEqual(repeated["reference"],"Bhagavad Gita 2.47")
            self.assertFalse(runtime.session_status()["current_completed"])
            nxt=runtime.control("next",explain=None)
            self.assertEqual(nxt["reference"],"Bhagavad Gita 2.48")
            self.assertTrue(runtime.gita.is_completed(2,47))
            self.assertEqual(nxt["completed_previous"]["reference"],"2.47")
            self.assertFalse(runtime.session_status()["current_completed"])

    def test_gita_response_is_directly_renderable_in_odia_chat(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=self._runtime(td)
            out=runtime.verse(2,47,language="or",explain=lambda _:"ପାର୍ଥ, କର୍ମ କର; ଫଳରେ ଆସକ୍ତ ହେଅନି।")
            self.assertIn("ଭଗବଦ୍ ଗୀତା 2.47",out["text"])
            self.assertIn("ପୁଣି କୁହ",out["text"])
            self.assertIn("ଆଗକୁ",out["text"])
            self.assertIn("ପଛକୁ",out["text"])

    def test_request_detector_only_hijacks_gita_or_active_session_controls(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=self._runtime(td)
            self.assertFalse(runtime.matches_request("ମୋ project health check କର"))
            self.assertTrue(runtime.matches_request("Krishna Gita 2.47 kuha"))
            runtime.verse(2,47,language="or",explain=None)
            self.assertTrue(runtime.matches_request("ଆଗକୁ"))
            self.assertTrue(runtime.matches_request("ପୁଣି କୁହ"))
            self.assertFalse(runtime.matches_request("ମୋ project deploy କର"))

    def test_short_odia_controls_work_without_repeating_gita(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=self._runtime(td)
            runtime.parse_request("Krishna Gita 2.47 kuha",explain=None)
            nxt=runtime.parse_request("ଆଗକୁ",explain=None)
            self.assertEqual(nxt["reference"],"Bhagavad Gita 2.48")
            again=runtime.parse_request("ପୁଣି କୁହ",explain=None)
            self.assertEqual(again["reference"],"Bhagavad Gita 2.48")
            paused=runtime.parse_request("ଥାଅ",explain=None)
            self.assertTrue(paused["session"]["paused"])
            resumed=runtime.parse_request("ଚାଲୁ କର",explain=None)
            self.assertFalse(resumed["session"]["paused"])

    def test_global_owner_conversation_defaults_to_odia(self):
        status=KrishnaCharacterPersona.status()
        self.assertEqual(status["global_conversation_language"],"or")
        self.assertIn("all ordinary KRISHNA conversation",KrishnaCharacterPersona.prompt_contract())
        self.assertIn("Odia",KrishnaCharacterPersona.prompt_contract())

    def test_voice_stack_exposes_dedicated_sanskrit_boundary(self):
        status=KrishnaVoiceStack().status()
        self.assertEqual(status["global_conversation_language"],"or")
        self.assertIn("sanskrit_tts",status)
        self.assertEqual(status["sanskrit_tts"]["language"],"sa")


class GitaWiringContractTests(unittest.TestCase):
    def test_normal_chat_routes_gita_requests_before_generic_model(self):
        text = (Path(__file__).resolve().parents[1] / "krishna_core" / "orchestrator.py").read_text(encoding="utf-8-sig")
        self.assertIn("self.gita_shloka.matches_request(message)", text)
        self.assertIn('"provider":"gita-gyan"', text)
        self.assertIn("GLOBAL CONVERSATION LANGUAGE OVERRIDE", text)

    def test_orchestrator_wires_gita_runtime(self):
        text = (Path(__file__).resolve().parents[1] / "krishna_core" / "orchestrator.py").read_text(encoding="utf-8-sig")
        self.assertIn("from .gita_gyan import GitaGyan", text)
        self.assertIn("self.gita_gyan = GitaGyan", text)
        self.assertIn("def gita_daily_lesson", text)

    def test_server_exposes_gita_routes(self):
        text = (Path(__file__).resolve().parents[1] / "krishna_core" / "server.py").read_text(encoding="utf-8-sig")
        self.assertIn('"/api/gita/status"', text)
        self.assertIn('"/api/gita/session"', text)
        self.assertIn('"/api/gita/session/control"', text)
        self.assertIn('"/api/gita/today"', text)
        self.assertIn('"/api/gita/revise"', text)
        self.assertIn('"/api/gita/speak"', text)

    def test_mobile_policy_allows_gita_learning_routes(self):
        text = (Path(__file__).resolve().parents[1] / "krishna_core" / "remote_access.py").read_text(encoding="utf-8-sig")
        self.assertIn('"/api/gita/status"', text)
        self.assertIn('"/api/gita/today"', text)
        self.assertIn('"/api/gita/revise"', text)

    def test_windows_build_bundles_gita_data(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github" / "workflows" / "build-console.yml").read_text(encoding="utf-8-sig")
        local_build = (root / "BUILD_KRISHNA_AGI.ps1").read_text(encoding="utf-8-sig")
        self.assertGreaterEqual(workflow.count('core/krishna_core/data;krishna_core/data'), 2)
        self.assertIn('core\\krishna_core\\data;krishna_core\\data', local_build)


if __name__ == "__main__":
    unittest.main()
