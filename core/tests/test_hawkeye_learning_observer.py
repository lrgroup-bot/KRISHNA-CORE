import tempfile
import unittest
from pathlib import Path

from krishna_core.hawkeye_learning_observer import HawkeyeLearningObserver


class FakeUniversal:
    def ingest(self, **kwargs):
        return {
            "learning_id": "learn-1",
            "rishi": "kanada",
            "unknown_resolution": None,
            "captured": kwargs,
        }
    def classify_sound_request(self, text, observations=None):
        return {"requested_classification": True, "observations": observations or {}}


class FakeBrahma:
    def intake(self, **kwargs):
        return {
            "decision_id": "brahma-1",
            "lead_rishi": "kanada",
            "team": ["kanada", "gautama", "veda-vyasa"],
            "should_learn": True,
            "captured": kwargs,
        }


class FakeCouncil:
    def specialist_team(self, topic, limit=6):
        return {
            "topic": topic,
            "members": [
                {"id": "kanada"},
                {"id": "gautama"},
                {"id": "veda-vyasa"},
            ],
        }


class FakeMemory:
    def __init__(self):
        self.rows = []
    def audit(self, *args):
        self.rows.append(args)


class HawkeyeLearningObserverTests(unittest.TestCase):
    def make(self, root):
        return HawkeyeLearningObserver(
            root,
            universal_learning=FakeUniversal(),
            brahma=FakeBrahma(),
            council=FakeCouncil(),
            memory=FakeMemory(),
        )

    def test_video_or_book_finding_routes_to_rishi_without_raw_media(self):
        with tempfile.TemporaryDirectory() as td:
            observer=self.make(Path(td))
            row=observer.capture(
                utterance="learn this book page",
                source_type="book",
                source_ref="page-12-sha256:abc",
                modalities=["image","text"],
                subject="electrical circuit theory",
                analysis="The page explains a bridge rectifier and filtering capacitor.",
                confidence=0.82,
                evidence_state="OBSERVED",
            )
            self.assertEqual(row["lead_rishi"],"kanada")
            self.assertIn("gautama",row["rishi_team"])
            self.assertFalse(row["storage_policy"]["raw_media_stored_here"])
            self.assertTrue(row["storage_policy"]["distilled_finding_only"])
            self.assertTrue((Path(td)/"observer-ledger.jsonl").is_file())

    def test_sensitive_auth_text_is_redacted_before_learning(self):
        with tempfile.TemporaryDirectory() as td:
            observer=self.make(Path(td))
            row=observer.capture(
                utterance="learn this",
                source_type="screen",
                source_ref="screen-1",
                modalities=["image"],
                subject="login screen",
                analysis="password: SuperSecret123",
                confidence=0.7,
                evidence_state="OBSERVED",
            )
            self.assertNotIn("SuperSecret123",row["finding"])
            self.assertIn("[SECRET REDACTED]",row["finding"])

    def test_unknown_face_cannot_become_social_identity_search(self):
        with tempfile.TemporaryDirectory() as td:
            observer=self.make(Path(td))
            plan=observer.public_research_plan(
                known_identity="",
                identity_basis="unknown_face",
                public_clues=[],
                subject="person in camera",
            )
            self.assertFalse(plan["identity_allowed"])
            self.assertFalse(plan["face_to_social_search"])
            self.assertFalse(any("instagram.com" in q for q in plan["queries"]))

    def test_enrolled_or_user_supplied_identity_can_use_public_text_search(self):
        with tempfile.TemporaryDirectory() as td:
            observer=self.make(Path(td))
            plan=observer.public_research_plan(
                known_identity="Example Person",
                identity_basis="enrolled_consented_match",
                public_clues=["Example Company"],
                subject="",
            )
            self.assertTrue(plan["identity_allowed"])
            self.assertTrue(any("linkedin.com" in q for q in plan["queries"]))
            self.assertFalse(plan["face_to_social_search"])

    def test_audio_routes_sound_observation(self):
        with tempfile.TemporaryDirectory() as td:
            observer=self.make(Path(td))
            row=observer.capture(
                utterance="learn this engine sound",
                source_type="audio",
                source_ref="clip-1",
                modalities=["audio"],
                subject="engine noise",
                analysis="Periodic metallic tick rises with RPM.",
                confidence=0.65,
                evidence_state="OBSERVED",
                audio_observations={"rpm": 1200},
            )
            self.assertTrue(row["sound"]["requested_classification"])


if __name__=="__main__":
    unittest.main()
