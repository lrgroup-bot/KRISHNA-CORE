"""Standalone learner tests must not reach KRISHNA or launch second workers."""
import os
import unittest
from unittest.mock import patch

from suryadev_extras import work_loop


class StandaloneIsolationTests(unittest.TestCase):
    def test_explicit_core_mission_refused_before_any_source_io(self):
        with patch.dict(os.environ,{"SURYADEV_STANDALONE_TEST":"1"}):
            with self.assertRaisesRegex(ValueError,"Standalone test forbids"):
                work_loop(None,30,True,"gemma3:4b",
                          plan_path="unused-local-plan.json",
                          core_mission_config="unused-core-config.json")

    def test_fleet_and_handoff_refused_before_any_source_io(self):
        with patch.dict(os.environ,{"SURYADEV_STANDALONE_TEST":"1"}):
            with self.assertRaisesRegex(ValueError,"Standalone test forbids"):
                work_loop(None,30,True,"gemma3:4b",fleet_mode=True)
            with self.assertRaisesRegex(ValueError,"Standalone test forbids"):
                work_loop(None,30,True,"gemma3:4b",sync_book_handoff=True)


if __name__=="__main__":
    unittest.main()
