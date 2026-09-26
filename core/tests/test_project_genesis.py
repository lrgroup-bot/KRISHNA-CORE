import tempfile
import unittest

from krishna_core.project_genesis import ProjectGenesis


class ProjectGenesisTests(unittest.TestCase):
    def test_intake_is_mandatory_before_scope_lock(self):
        with tempfile.TemporaryDirectory() as td:
            g = ProjectGenesis(td)
            started = g.start("demo", "Build a vehicle app")
            self.assertFalse(started["intake_ready"])
            self.assertIn("timeline", started["missing_intake"])
            g.update_intake(
                "demo", deadline_hours=48, platforms=["Android", "Web"],
                core_requirements=["vehicle list", "mark sold"],
                ui_mode="existing",
            )
            proposed = g.propose_enhancements("demo")
            self.assertTrue(proposed["enhancements"]["proposals"])
            g.decide_enhancements("demo", ["quality-observability", "security-privacy"])
            locked = g.lock_scope("demo")
            self.assertTrue(locked["implementation_allowed"])
            self.assertTrue(locked["goal_contract"]["owner_scope_locked"])
            self.assertIn("vehicle list", locked["goal_contract"]["completion_conditions"])

    def test_abcd_design_must_be_selected(self):
        with tempfile.TemporaryDirectory() as td:
            g = ProjectGenesis(td)
            g.start("demo", "Build app")
            g.update_intake(
                "demo", deadline_hours=24, platforms=["Android"],
                core_requirements=["home screen"], ui_mode="research_abcd",
            )
            g.propose_enhancements("demo")
            g.decide_enhancements("demo", [])
            with self.assertRaises(RuntimeError):
                g.lock_scope("demo")
            g.record_design_selection("demo", "session-1", "candidate-b", "B")
            self.assertTrue(g.lock_scope("demo")["implementation_allowed"])

    def test_locked_scope_rejects_intake_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            g = ProjectGenesis(td)
            g.start("demo", "Build app")
            g.update_intake("demo", deadline_hours=4, platforms=["Web"], core_requirements=["login"], ui_mode="none")
            g.propose_enhancements("demo")
            g.decide_enhancements("demo", [])
            g.lock_scope("demo")
            with self.assertRaises(RuntimeError):
                g.update_intake("demo", deadline_hours=8)


if __name__ == "__main__":
    unittest.main()
