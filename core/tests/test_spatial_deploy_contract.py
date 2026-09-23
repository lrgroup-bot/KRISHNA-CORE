import unittest
from pathlib import Path


class SpatialDeployContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path(__file__).resolve().parents[2]

    def test_generated_spatial_artifacts_are_ignored(self):
        text=(self.repo/".gitignore").read_text(encoding="utf-8")
        self.assertIn("app/spatial-ui/node_modules/",text)
        self.assertIn("app/spatial-ui/dist/",text)

    def test_deploy_build_does_not_create_package_lock_and_rechecks_cleanliness(self):
        text=(self.repo/"scripts"/"DEPLOY_KRISHNA_ONCE.ps1").read_text(encoding="utf-8")
        self.assertIn("--package-lock=false",text)
        self.assertIn("SPATIAL UI BUILD DIRTY THE SOURCE REPOSITORY",text)
        self.assertIn("git -C $Source status --porcelain",text)

    def test_spatial_runtime_has_version_marker_and_subpath_base(self):
        index=(self.repo/"app"/"spatial-ui"/"index.html").read_text(encoding="utf-8")
        vite=(self.repo/"app"/"spatial-ui"/"vite.config.ts").read_text(encoding="utf-8")
        server=(self.repo/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8")
        self.assertIn('data-krishna-spatial-ui="2026.09"',index)
        self.assertIn("base: '/spatial/'",vite)
        self.assertIn('path.startswith("/spatial/")',server)
        self.assertIn('path in ("/spatial", "/spatial-preview")',server)
        self.assertIn("KRISHNA_SPATIAL_UI_DEFAULT",server)
        self.assertIn("spatial_ui_index()",server)


if __name__=="__main__":
    unittest.main()
