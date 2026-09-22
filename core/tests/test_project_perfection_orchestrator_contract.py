import unittest
from pathlib import Path


class ProjectPerfectionOrchestratorContract(unittest.TestCase):
    def test_finish_action_can_apply_and_roll_back_after_live_verification(self):
        source=(Path(__file__).resolve().parents[1]/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        start=source.index("def project_perfection_finish_action")
        end=source.index("def project_design_research_action",start)
        block=source[start:end]
        self.assertIn('payload.get("apply_verified",False)',block)
        self.assertIn('promote_candidate(token,approved=True)',block)
        self.assertIn('post_apply_verify(',block)
        self.assertIn('self.promotions.rollback(',block)
        self.assertIn('VERIFIED_AND_APPLIED',block)
        self.assertIn('ROLLED_BACK_POST_APPLY',block)

    def test_operator_finish_script_requests_apply(self):
        script=(Path(__file__).resolve().parents[2]/"scripts"/"FINISH_KRISHNA_PROJECT.ps1").read_text(encoding="utf-8")
        self.assertIn("apply_verified=$true",script)
        self.assertIn("/api/project-perfection/finish",script)


if __name__=="__main__":
    unittest.main()
