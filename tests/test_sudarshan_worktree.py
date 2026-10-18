import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tools.sudarshan_worktree import isolated_worktree, execute, change_report


def git(root, *argv):
    subprocess.run(['git', '-C', str(root), *argv], check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class WorktreeTests(unittest.TestCase):
    def test_changes_are_discarded_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / 'repo'
            repo.mkdir()
            git(repo, 'init', '-q')
            (repo / 'app.txt').write_text('original')
            git(repo, 'add', 'app.txt')
            git(repo, '-c', 'user.email=test@example.invalid',
                '-c', 'user.name=Test', 'commit', '-qm', 'initial')
            with isolated_worktree(repo) as checkout:
                command = [sys.executable, '-c',
                           "from pathlib import Path; Path('app.txt').write_text('changed'); Path('new.txt').write_text('new')"]
                self.assertTrue(execute(checkout, command)['passed'])
                report = change_report(checkout)
                self.assertTrue(report['dirty'])
                self.assertIn('new.txt', report['untracked_files'])
                self.assertIn('changed', report['tracked_patch'])
                self.assertEqual((repo / 'app.txt').read_text(), 'original')
            self.assertFalse(checkout.exists())
            self.assertEqual((repo / 'app.txt').read_text(), 'original')

    def test_unapproved_relative_executable_blocked(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / 'repo'
            repo.mkdir()
            git(repo, 'init', '-q')
            (repo / 'file').write_text('a')
            git(repo, 'add', 'file')
            git(repo, '-c', 'user.email=test@example.invalid',
                '-c', 'user.name=Test', 'commit', '-qm', 'initial')
            with isolated_worktree(repo) as checkout:
                with self.assertRaises(ValueError):
                    execute(checkout, ['python', '-V'])

    def test_rollback_after_exception(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / 'repo'
            repo.mkdir()
            git(repo, 'init', '-q')
            (repo / 'file').write_text('a')
            git(repo, 'add', 'file')
            git(repo, '-c', 'user.email=test@example.invalid',
                '-c', 'user.name=Test', 'commit', '-qm', 'initial')
            with self.assertRaisesRegex(RuntimeError, 'example'):
                with isolated_worktree(repo) as checkout:
                    (checkout / 'file').write_text('mutated')
                    raise RuntimeError('example')
            self.assertEqual((repo / 'file').read_text(), 'a')
            self.assertFalse(checkout.exists())


if __name__ == '__main__':
    unittest.main()
