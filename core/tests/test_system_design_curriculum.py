import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from krishna_core.rishi_council import RishiCouncil
from krishna_core.system_design_curriculum import (
    CURRICULUM,
    SystemDesignCurriculum,
    SystemDesignLearningScheduler,
)


class SystemDesignCurriculumTests(unittest.TestCase):
    def make_curriculum(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return SystemDesignCurriculum(Path(temp.name))

    def test_curriculum_has_both_alex_xu_volumes_and_synthesis(self):
        curriculum = self.make_curriculum()
        schedule = curriculum.schedule()
        self.assertEqual(len(CURRICULUM), 30)
        self.assertEqual({x["volume"] for x in schedule["modules"]}, {0, 1, 2})
        self.assertEqual(schedule["modules"][0]["id"], "v1-01-scale")
        self.assertEqual(schedule["modules"][14]["id"], "v1-15-drive")
        self.assertEqual(schedule["modules"][15]["id"], "v2-01-proximity")
        self.assertEqual(schedule["modules"][-1]["id"], "synthesis-02")

    def test_curriculum_uses_official_public_sources_not_pdf_copy(self):
        curriculum = self.make_curriculum()
        policy = curriculum.source_policy()
        urls = " ".join(x["url"] for x in policy["official_index"]).lower()
        self.assertIn("alex-xu-system/bytebytego", urls)
        self.assertIn("bytebytegohq/system-design-101", urls)
        self.assertNotIn(".pdf", urls)
        self.assertTrue(any("unauthorized full-book" in rule for rule in policy["rules"]))

    def test_next_assignment_starts_with_scale_module(self):
        curriculum = self.make_curriculum()
        now = datetime(2026, 10, 1, 3, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        assignment = curriculum.next_assignment(now)
        self.assertEqual(assignment["id"], "v1-01-scale")
        self.assertEqual(assignment["lead_rishi"], "bharadvaja")
        self.assertIn("gautama", assignment["team"])
        self.assertIn("veda-vyasa", assignment["team"])

    def test_verified_result_moves_to_next_due_module(self):
        curriculum = self.make_curriculum()
        now = datetime(2026, 10, 2, 3, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        curriculum.record_result(
            "v1-01-scale", mission_id="m1", run_id="r1",
            scorecard={"cross_checked_claims": 2, "source_count": 5},
        )
        assignment = curriculum.next_assignment(now)
        self.assertEqual(assignment["id"], "v1-02-estimation")

    def test_weak_result_retries_same_module(self):
        curriculum = self.make_curriculum()
        now = datetime(2026, 10, 2, 15, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        curriculum.record_result(
            "v1-01-scale",
            scorecard={"cross_checked_claims": 0, "source_count": 1},
        )
        assignment = curriculum.next_assignment(now)
        self.assertEqual(assignment["id"], "v1-01-scale")
        self.assertEqual(assignment["attempt"], 2)

    def test_rishi_council_routes_system_design_specialists(self):
        council = RishiCouncil()
        ids = [x["id"] for x in council.select(
            "distributed systems rate limiting message queues consistent hashing system design", 6
        )]
        self.assertIn("jamadagni", ids)
        self.assertIn("pingala", ids)
        self.assertIn("bharadvaja", ids)
        self.assertIn("gautama", ids)
        self.assertIn("veda-vyasa", ids)

    def test_scheduler_allows_retry_window_but_only_one_verified_module_per_day(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        results = [
            {"ran": False, "reason": "resource_gate"},
            {"ran": True, "curriculum_module": {"status": "verified"}},
        ]

        def run_tick():
            return results.pop(0)

        scheduler = SystemDesignLearningScheduler(Path(temp.name), run_tick, poll_seconds=300)
        first = datetime(2026, 10, 1, 3, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        retry = datetime(2026, 10, 1, 15, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        late = datetime(2026, 10, 1, 20, 0, tzinfo=ZoneInfo("Asia/Kolkata"))

        self.assertEqual(scheduler.run_once(now=first)["status"], "completed")
        self.assertEqual(scheduler.run_once(now=retry)["status"], "completed")
        self.assertEqual(scheduler.run_once(now=late)["status"], "not_due")


if __name__ == "__main__":
    unittest.main()
