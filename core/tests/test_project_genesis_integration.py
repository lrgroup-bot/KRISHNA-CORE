import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]


class ProjectGenesisIntegrationContractTests(unittest.TestCase):
    def test_orchestrator_registers_genesis_scheduler_staffing_and_worktrees(self):
        text=(ROOT/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        for action in (
            "project.genesis.start",
            "project.genesis.intake",
            "project.genesis.enhancements",
            "project.genesis.decide_enhancements",
            "project.genesis.design_selected",
            "project.genesis.lock_scope",
            "engineering.plan",
            "engineering.staff",
            "engineering.swarm.status",
            "engineering.worktree.create",
        ):
            self.assertIn(f'"{action}"',text)
        self.assertIn("self.missions.create(",text)
        self.assertIn("self.project_brain.provision(project)",text)

    def test_server_exposes_genesis_and_staffing_surfaces(self):
        text=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8")
        for route in (
            "/api/project-genesis/status",
            "/api/project-genesis/start",
            "/api/project-genesis/intake",
            "/api/project-genesis/enhancements",
            "/api/project-genesis/decide",
            "/api/project-genesis/lock",
            "/api/project-genesis/plan",
            "/api/engineering/staff",
            "/api/engineering/swarm/status",
            "/api/engineering/worktree/create",
        ):
            self.assertIn(route,text)

    def test_design_studio_submit_satisfies_genesis_design_gate(self):
        text=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8")
        submit=text.index('if post_path == "/api/design-studio/submit":')
        tail=text[submit:submit+9000]
        self.assertIn("project_genesis.record_design_selection",tail)


if __name__=="__main__":
    unittest.main()
