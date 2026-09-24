from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from krishna_core.gita_gyan import GitaGyan
from krishna_core.gita_performance import GitaPerformanceEngine
from krishna_core.krishna_shloka_orchestrator import KrishnaShlokaOrchestrator


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

    def test_windows_build_bundles_gita_data(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github" / "workflows" / "build-console.yml").read_text(encoding="utf-8-sig")
        local_build = (root / "BUILD_KRISHNA_AGI.ps1").read_text(encoding="utf-8-sig")
        self.assertGreaterEqual(workflow.count('core/krishna_core/data;krishna_core/data'), 2)
        self.assertIn('core\\krishna_core\\data;krishna_core\\data', local_build)


class GitaContinuousSessionTests(unittest.TestCase):
    def test_navigation_does_not_require_completion(self):
        with tempfile.TemporaryDirectory() as td:
            gita=GitaGyan(Path(td))
            state,row=gita.start_session(1,1,"or","deep")
            self.assertEqual((row["chapter"],row["verse"]),(1,1))
            self.assertEqual(gita.status()["completed_count"],0)
            state,row=gita.navigate_session("next")
            self.assertEqual((row["chapter"],row["verse"]),(1,2))
            self.assertEqual(gita.status()["completed_count"],0)
            self.assertTrue(state["next_does_not_require_completion"])
            self.assertFalse(state["completion_required_for_navigation"])

    def test_repeat_previous_forward_and_goto_are_owner_controlled(self):
        with tempfile.TemporaryDirectory() as td:
            gita=GitaGyan(Path(td))
            gita.start_session(2,47)
            state,row=gita.navigate_session("repeat")
            self.assertEqual((row["chapter"],row["verse"]),(2,47))
            self.assertEqual(state["repeat_count"],1)
            _state,row=gita.navigate_session("previous")
            self.assertEqual((row["chapter"],row["verse"]),(2,46))
            _state,row=gita.navigate_session("forward")
            self.assertEqual((row["chapter"],row["verse"]),(2,47))
            _state,row=gita.navigate_session("goto",chapter=11,verse=50)
            self.assertEqual((row["chapter"],row["verse"]),(11,50))

    def test_complete_is_explicit_metadata_and_does_not_move_session(self):
        with tempfile.TemporaryDirectory() as td:
            gita=GitaGyan(Path(td))
            gita.start_session(3,1)
            marked=gita.mark_complete()
            self.assertTrue(marked["completed"])
            self.assertFalse(marked["navigation_affected"])
            state=gita.session_status()
            self.assertEqual((state["chapter"],state["verse"]),(3,1))
            _state,row=gita.navigate_session("next")
            self.assertEqual((row["chapter"],row["verse"]),(3,2))
            unmarked=gita.mark_complete(3,1,False)
            self.assertFalse(unmarked["completed"])

    def test_search_can_resolve_exact_reference(self):
        with tempfile.TemporaryDirectory() as td:
            gita=GitaGyan(Path(td))
            found=gita.search("Bhagavad Gita 2.47")
            self.assertEqual(len(found),1)
            self.assertEqual((found[0]["chapter"],found[0]["verse"]),(2,47))


class GitaPerformanceTests(unittest.TestCase):
    def test_all_700_verses_get_unique_performance_ids(self):
        with tempfile.TemporaryDirectory() as td:
            gita=GitaGyan(Path(td))
            engine=GitaPerformanceEngine()
            records=engine.records_for(gita._load_corpus())
            self.assertEqual(len(records),700)
            self.assertEqual(len({x["performance_id"] for x in records}),700)
            self.assertTrue(all(x["renderer_contract"]["one_identity"] for x in records))

    def test_special_scriptural_performance_transitions(self):
        engine=GitaPerformanceEngine()
        self.assertEqual(engine.performance(2,10)["family"],"SMILING_TEACHER")
        self.assertEqual(engine.performance(2,47)["family"],"KARMA_YOGA_TEACHER")
        self.assertEqual(engine.performance(11,32)["family"],"VISHVARUPA")
        self.assertEqual(engine.performance(11,50)["family"],"REASSURING_PERSONAL_FORM")
        self.assertEqual(engine.performance(18,63)["family"],"CLOSING_COUNSEL")


class _FakeAvatar:
    def __init__(self):self.last=None
    def set_state(self,state,**params):
        self.last={"state":state,"params":params}
        return dict(self.last)


class KrishnaShlokaOrchestratorTests(unittest.TestCase):
    def test_presented_verse_has_separate_sanskrit_and_global_odia_explanation(self):
        with tempfile.TemporaryDirectory() as td:
            gita=GitaGyan(Path(td))
            avatar=_FakeAvatar()
            runtime=KrishnaShlokaOrchestrator(
                gita,avatar,explain=lambda _prompt:"ପାର୍ଥ, ଏହା କର୍ମ ଓ ଫଳାସକ୍ତି ବିଷୟରେ ଶିକ୍ଷା।"
            )
            out=runtime.start(2,47)
            self.assertEqual(out["language"],"or")
            self.assertEqual(out["speech_sequence"][0]["language"],"sa")
            self.assertEqual(out["speech_sequence"][1]["language"],"or")
            self.assertEqual(out["performance"]["family"],"KARMA_YOGA_TEACHER")
            self.assertFalse(out["navigation"]["completion_required_for_next"])
            self.assertTrue(out["navigation"]["owner_controls_progression"])

    def test_repeat_does_not_advance(self):
        with tempfile.TemporaryDirectory() as td:
            gita=GitaGyan(Path(td))
            runtime=KrishnaShlokaOrchestrator(gita,_FakeAvatar(),explain=None)
            runtime.start(4,7,include_explanation=False)
            again=runtime.control("repeat",include_explanation=False)
            self.assertEqual((again["chapter"],again["verse"]),(4,7))
            nxt=runtime.control("next",include_explanation=False)
            self.assertEqual((nxt["chapter"],nxt["verse"]),(4,8))


class GitaContinuousWiringTests(unittest.TestCase):
    def test_server_exposes_owner_controlled_session_routes(self):
        text=(Path(__file__).resolve().parents[1]/"krishna_core"/"server.py").read_text(encoding="utf-8-sig")
        for route in (
            '"/api/gita/session"','"/api/gita/verse"','"/api/gita/performance"',
            '"/api/gita/session/start"','"/api/gita/session/control"',
            '"/api/gita/search"','"/api/gita/complete"',
        ):
            self.assertIn(route,text)
        self.assertIn('"ପୁଣି"',text)
        self.assertIn('"ଆଗକୁ"',text)
        self.assertIn('"ପଛକୁ"',text)

    def test_private_mobile_policy_includes_new_gita_controls(self):
        text=(Path(__file__).resolve().parents[1]/"krishna_core"/"remote_access.py").read_text(encoding="utf-8-sig")
        self.assertIn('"/api/gita/session/control"',text)
        self.assertIn('"/api/gita/performance"',text)
        self.assertIn('"/api/gita/search"',text)



if __name__ == "__main__":
    unittest.main()
