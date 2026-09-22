import tempfile
import unittest
from pathlib import Path

from krishna_core.design_implementation import DesignImplementationGuard


class DesignImplementationGuardTests(unittest.TestCase):
    def test_preview_token_requires_internal_preview_route(self):
        token=DesignImplementationGuard.preview_token("/api/design-studio/preview?id=abc123")
        self.assertEqual(token,"abc123")
        with self.assertRaises(ValueError):
            DesignImplementationGuard.preview_token("https://example.com")

    def test_context_and_patch_are_frontend_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"src").mkdir()
            (root/"src"/"App.tsx").write_text("export default function App(){return <main>Hello</main>}\n",encoding="utf-8")
            (root/".env").write_text("SECRET=x\n",encoding="utf-8")
            context=DesignImplementationGuard.collect_context(root)
            self.assertEqual(context["file_count"],1)
            clean=DesignImplementationGuard.validate_patch(root,[{
                "path":"src/App.tsx",
                "content":"export default function App(){return <main>Better</main>}\n",
            }])
            self.assertEqual(clean[0]["path"],"src/App.tsx")
            with self.assertRaises(PermissionError):
                DesignImplementationGuard.validate_patch(root,[{"path":".env","content":"SECRET=y"}])

    def test_submit_endpoint_keeps_transactional_apply_and_post_verify_rollback(self):
        server=(Path(__file__).resolve().parents[1]/"krishna_core"/"server.py").read_text(encoding="utf-8")
        start=server.index('if post_path == "/api/design-studio/submit":')
        end=server.index('if post_path == "/api/project-perfection/visual-intent":',start)
        block=server[start:end]
        self.assertIn('project.design.implement',block)
        self.assertIn('promote_candidate(token,approved=True)',block)
        self.assertIn('verify_design_candidate(',block)
        self.assertIn('orch.promotions.rollback(',block)
        self.assertIn('rolled_back_post_verify',block)

    def test_arbitrary_new_source_file_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with self.assertRaises(PermissionError):
                DesignImplementationGuard.validate_patch(root,[{"path":"src/New.tsx","content":"export default 1"}])


if __name__=="__main__":
    unittest.main()
