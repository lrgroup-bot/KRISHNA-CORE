import os
import unittest
from pathlib import Path


def repository_root():
    configured=str(os.environ.get("KRISHNA_SOURCE_ROOT") or "").strip()
    return Path(configured).resolve() if configured else Path(__file__).resolve().parents[2]


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

    def test_visual_editor_is_point_drag_voice_and_fail_safe_apply(self):
        root=Path(__file__).resolve().parents[1]
        editor=(root/"visual_editor.html").read_text(encoding="utf-8")
        server=(root/"krishna_core"/"server.py").read_text(encoding="utf-8")
        self.assertIn("pointerdown",editor)
        self.assertIn("setPointerCapture",editor)
        self.assertIn("SpeechRecognition",editor)
        self.assertIn("/api/project-perfection/visual-edit/stage",editor)
        self.assertIn("/api/project-perfection/visual-edit/apply",editor)
        self.assertIn('"/api/project-perfection/visual-edit/apply"',server)
        self.assertIn("post_apply_verify(",server)
        self.assertIn("promotions.rollback(",server)

    def test_mobile_emulator_retest_uses_single_script_command(self):
        root=repository_root()
        workflow=(root/".github"/"workflows"/"build-mobile-v3.yml").read_text(encoding="utf-8")
        verifier=(root/"scripts"/"VERIFY_KRISHNA_APK.py").read_text(encoding="utf-8")
        self.assertIn("scripts/VERIFY_KRISHNA_APK.py",workflow)
        self.assertNotIn("script: PYTHONPATH=core python -c 'import json,sys;",workflow)
        self.assertIn("ArtifactExecutor().apk",verifier)

    def test_operator_finish_script_requests_apply(self):
        script=(repository_root()/"scripts"/"FINISH_KRISHNA_PROJECT.ps1").read_text(encoding="utf-8")
        self.assertIn("apply_verified=$true",script)
        self.assertIn("/api/project-perfection/finish",script)


if __name__=="__main__":
    unittest.main()
