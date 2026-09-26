import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from krishna_core.git_worktrees import GitWorktreeManager


@unittest.skipUnless(shutil.which("git"), "git is required")
class GitWorktreeManagerTests(unittest.TestCase):
    def _git(self, root, *args):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)

    def test_create_and_remove_real_worktree(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            repo = base / "repo"
            repo.mkdir()
            self._git(repo, "init")
            self._git(repo, "config", "user.email", "krishna@example.invalid")
            self._git(repo, "config", "user.name", "KRISHNA Test")
            (repo / "README.md").write_text("demo\n", encoding="utf-8")
            self._git(repo, "add", "README.md")
            self._git(repo, "commit", "-m", "initial")
            manager = GitWorktreeManager(repo, base / "worktrees")
            created = manager.create("demo", "backend", mission_id="m1")
            self.assertTrue(Path(created["path"]).is_dir())
            self.assertTrue(created["branch"].startswith("krishna/demo/backend-"))
            rows = manager.list()
            self.assertTrue(any(Path(x["path"]).resolve() == Path(created["path"]).resolve() for x in rows))
            removed = manager.remove(created["path"], delete_branch=True)
            self.assertTrue(removed["removed"])
            self.assertFalse(Path(created["path"]).exists())

    def test_refuses_worktree_root_inside_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(ValueError):
                GitWorktreeManager(root, root / ".worktrees")


if __name__ == "__main__":
    unittest.main()
